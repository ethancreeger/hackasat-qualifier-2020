import click
import struct
import timeit

SAMPLE_RATE = 102400
SAMPLE_PERIOD = 1.0 / float(SAMPLE_RATE)
SAMPLE_FMT = "<ff"
SPIKE_THRESHOLD = -65

def calc_and_store_position(
    verbose,
    output_fp,
    last_on_time,
    last_azimuth_off_time,
    last_elevation_off_time
):
    azimuth_duty = \
        (last_azimuth_off_time - last_on_time) / 0.02
    elevation_duty = \
        (last_elevation_off_time - last_on_time) / 0.02

    azimuth_motor_deg = ((azimuth_duty - 0.05) / 0.30) * 180
    elevation_motor_deg = ((elevation_duty - 0.05) / 0.30) * 180

    orientation = 0
    elevation_inverted = False

    if elevation_motor_deg > 90:
        orientation = 180
        elevation_inverted = True

    #azimuth_deg = abs(
    #    (azimuth_motor_deg - orientation + 180) % 360 - 180
    #)
    azimuth_deg = azimuth_motor_deg + orientation

    if elevation_inverted:
        elevation_deg = 180 - elevation_motor_deg
    else:
        elevation_deg = elevation_motor_deg

    if (
        azimuth_deg > 360 or
        azimuth_deg < 0 or
        elevation_deg > 180 or
        elevation_deg < 0
    ):
        if verbose:
            print(
                'bad position with az',
                azimuth_deg,
                'and el',
                elevation_deg
            )
        return

    # store an antenna aiming. we'll compare these positions against satellite
    # orbits later on to determine what the ground station was tracking
    output_fp.write(str({
        'time': last_on_time,
        'azimuth': azimuth_deg,
        'elevation': elevation_deg
    }) + '\n')

# read samples from bin and convert them to azimuth and elevation motor pwm
# values. store them in output_fp
def convert_bin(verbose, bin_fp, output_fp):
    sample_id = 0
    power_event_id = 0
    azimuth_on = False
    elevation_on = False

    last_on_time = None
    last_azimuth_off_time = None
    last_elevation_off_time = None

    while True:
        try:
            data = bin_fp.read(8)
            if len(data) < 8:
                break

            time = sample_id * SAMPLE_PERIOD
            azimuth_sample, elevation_sample = struct.unpack_from(
                SAMPLE_FMT,
                data
            )

            # frequency spike at least this high is an edge
            if (
                azimuth_sample > SPIKE_THRESHOLD or
                elevation_sample > SPIKE_THRESHOLD
            ):
                # if we're on 50hz, it's power "on" for both the azimuth and
                # the elevation antenna motors
                fifty_hz = time % 0.02
                
                # allow a little wiggle room around the % 0.02
                if fifty_hz != 0 and (
                    fifty_hz > 0.01999 or
                    fifty_hz < 0.00001
                ):
                    fifty_hz = 0

                # zero here means we're on 50hz, so this is a power on event
                if fifty_hz == 0:
                    # if both are already on, we're getting a duped event or
                    # we missed a power off. let this point go.
                    if azimuth_on and elevation_on:
                        continue

                    # before we handle this "on" event and proceed to find
                    # corresponding elevation and azimuth offs, we need to
                    # calculate the last round's duty cycles and convert
                    # them to pwm values
                    if (
                        last_on_time is not None and
                        last_azimuth_off_time is not None and
                        last_elevation_off_time is not None
                    ):
                        calc_and_store_position(
                            verbose,
                            output_fp,
                            last_on_time,
                            last_azimuth_off_time,
                            last_elevation_off_time
                        )

                    last_on_time = time

                    # now that we've calculated our previous point, handle
                    # the power on event by marking the azimuth and
                    # elevation motor states True
                    azimuth_on = True
                    elevation_on = True
                    power_event_id += 1

                    if verbose:
                        print(
                            sample_id,
                            '\t\tboth on\t\t',
                            time,
                            azimuth_sample,
                            elevation_sample
                        )

                # this spike wasn't on 50hz, so it's a power off for either
                # or possibly both of the azimuth and elevation motors
                else:
                    # azimuth motor off
                    if azimuth_sample > SPIKE_THRESHOLD:
                        if azimuth_on:
                            azimuth_on = False
                            last_azimuth_off_time = time
                            power_event_id += 1

                            if verbose:
                                print(
                                    sample_id,
                                    '\t\tazimuth off\t',
                                    time,
                                    azimuth_sample,
                                    elevation_sample
                                )

                    # elevation motor off
                    if elevation_sample > SPIKE_THRESHOLD:
                        if elevation_on:
                            elevation_on = False
                            last_elevation_off_time = time
                            power_event_id += 1

                            if verbose:
                                print(
                                    sample_id,
                                    '\t\televation off\t',
                                    time,
                                    azimuth_sample,
                                    elevation_sample
                                )

                # sanity check
                state = (power_event_id - 1) % 3
                try:
                    if state == 0:
                        assert azimuth_on and elevation_on
                    else:
                        assert not (azimuth_on and elevation_on)
                except:
                    print(sample_id, '\t\tfailed sanity check')
                    break

                # used to cut sample run short for quicker iteration. full
                # run is ~94MB for 1.2m samples
                #if power_event_id > 10000:
                #    break

            sample_id += 1

        except EOFError:
            break

@click.command()
@click.option('--verbose', is_flag=True)
@click.argument('challenge')
@click.argument('signal')
def run(verbose, challenge, signal):
    'CHALLENGE: [examples, live], SIGNAL: [signal_0, signal_1, signal_2]'
    start = timeit.default_timer()
    if challenge not in ['examples', 'live']:
        print('invalid challenge')
        return
    if signal not in ['signal_0', 'signal_1', 'signal_2']:
        print('invalid signal')
        return

    try:
        bin_fp = open(challenge + '/' + signal + '.bin', 'rb')
        output_fp = open(challenge + '/' + signal + '.csv', 'w')
    except:
        print('file missing')
        return
    convert_bin(verbose, bin_fp, output_fp)

    stop = timeit.default_timer()
    print('runtime:', stop - start)  

if __name__ == '__main__':
    run()
