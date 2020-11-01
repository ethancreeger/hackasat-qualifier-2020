import click
from datetime import datetime, timezone, timedelta
from skyfield.api import load, EarthSatellite, Topos
import timeit

start = timeit.default_timer()

DURATION_SECONDS = 120
# allowed number of nonmatching observations per satellite before moving on
FAIL_THRESHOLD = 123
# allowed deviation from calculated position in degrees
AZ_ACCURACY_THRESHOLD = 0.45
EL_ACCURACY_THRESHOLD = 0.45

CHALLENGES = {
    'examples': {
        'trackasat_lat': 32.4907,
        'trackasat_long': 45.8304,
        'start_time_gmt': 1586249863.726371,
        'directory': 'examples',
        'signal_0': 'CANX-7',
        'signal_1': 'STARLINK-1113',
        'signal_2': 'SORTIE',
    },
    'live': {
        'trackasat_lat': -1.2833,
        'trackasat_long': 36.8167,
        'start_time_gmt': 1586154732.450837,
        'directory': 'live',
        'signal_0': 'STARLINK-41',
        'signal_1': 'COSMOS 2489',
        'signal_2': 'YUNHAI-2 4'
    }
}

@click.command()
@click.option('--verbose', default=False)
@click.argument('challenge')
@click.argument('signal')
def run(verbose, challenge, signal):
    '''
    challenge:
        examples
        live
    signal:
        signal_0
        signal_1
        signal_2
    '''
    if challenge not in CHALLENGES:
        print('invalid challenge')
        return
    if signal not in ['signal_0', 'signal_1', 'signal_2']:
        print('invalid signal')
        return
    challenge = CHALLENGES[challenge]

    positions = []
    with open(
        challenge['directory'] + '/' + signal + '.csv', 'r'
    ) as input_file:
        if not input_file:
            'file not found. did you run signal_to_pwm.py?'
            return
        for line in input_file:
            positions.append(eval(line))
    assert positions
    print('loaded', len(positions), 'positions\n')

    if verbose:
        print('positions[0].azimuth:', positions[0]['azimuth'])
        print('positions[0].elevation:', positions[0]['elevation'])
        print(
            'positions[len(positions) - 1][\'azimuth\']',
            positions[len(positions) - 1]['azimuth']
        )
        print(
            'positions[len(positions) - 1][\'elevation\']',
            positions[len(positions) - 1]['elevation']
        )

        positions_azimuth_range = \
            positions[0]['azimuth'] - positions[len(positions) - 1]['azimuth']
        positions_azimuth_range = \
            abs((positions_azimuth_range + 180) % 360 - 180)

        print('azimuth range:', positions_azimuth_range)
        print(
            'elevation range:',
            abs(positions[0]['elevation'] - \
                positions[len(positions) - 1]['elevation'])
        )
        print()

    sats = load.tle_file('examples/active.txt')
    print('loaded', len(sats), 'sats')

    ts = load.timescale(builtin=True)
    matches = []
    for sat in sats:
        print(sat)
        trackasat = Topos(
            challenge['trackasat_lat'],
            challenge['trackasat_long']
        )
        difference = sat - trackasat

        starting_time = datetime.fromtimestamp(
            challenge['start_time_gmt'],
            timezone.utc
        )
        final_time = starting_time + timedelta(0, 120)

        if verbose:
            t_starting = ts.utc(starting_time)
            topocentric = difference.at(t_starting)
            start_elevation, start_azimuth, distance = topocentric.altaz()
            print('start_azimuth:', start_azimuth.degrees)
            print('start_elevation:', start_elevation.degrees)

            t_final = ts.utc(final_time)
            topocentric = difference.at(t_final)
            final_elevation, final_azimuth, distance = topocentric.altaz()
            print('final_azimuth:', final_azimuth.degrees)
            print('final_elevation:', final_elevation.degrees)
            azimuth_range = start_azimuth.degrees - final_azimuth.degrees
            azimuth_range = abs((azimuth_range + 180) % 360 - 180)
            print('azimuth range:', azimuth_range)
            elevation_range = abs(start_elevation.degrees - final_elevation.degrees)
            print('elevation range:', elevation_range)

        success = True
        fail_count = 0
        for position in positions:
            working_time = starting_time + timedelta(0, position['time'])
            t_working = ts.utc(working_time)
            topocentric = difference.at(t_working)
            elevation, azimuth, distance = topocentric.altaz()

            if elevation.degrees < 0:
                success = False
                break

            if verbose:
                print(
                    azimuth.degrees,
                    elevation.degrees,
                    position['azimuth'],
                    position['elevation']
                )

            if (
                abs(azimuth.degrees - position['azimuth']) > \
                    AZ_ACCURACY_THRESHOLD or
                abs(elevation.degrees - position['elevation']) > \
                    EL_ACCURACY_THRESHOLD
            ):
                if verbose:
                    print(
                        'mismatch:',
                        azimuth.degrees - position['azimuth'],
                        elevation.degrees - position['elevation']
                    )
                fail_count += 1
                if fail_count > FAIL_THRESHOLD:
                    if verbose:
                        print('sat failed with fail_count:', fail_count)
                    success = False
                    break

        if success:
            matches.append({
                'name': sat.name,
                'fail_count': fail_count
            })

    print()
    print('expected: ' + challenge[signal])
    print('matches:')
    for match in matches:
        print(match)

    stop = timeit.default_timer()
    print('\nruntime:', stop - start)  

if __name__ == '__main__':
    run()
