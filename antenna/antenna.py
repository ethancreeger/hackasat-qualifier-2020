import sys
import click
from datetime import datetime, timezone, timedelta
from skyfield.api import load, EarthSatellite, Topos

EXAMPLES_FOLDER = 'examples'
OUTPUT_FILE = 'output.txt'
DURATION_SECONDS = 720

CHALLENGES = {
    'challenge0': {
        'trackasat_lat': 52.5341,
        'trackasat_long': 85.18,
        'satellite_name': 'PERUSAT 1',
        'start_time_gmt': 1586789933.820023,
        'diff': 'solution0.txt'
    },
    'challenge1': {
        'trackasat_lat': 19.8957,
        'trackasat_long': 75.3203,
        'satellite_name': 'MAROC-TUBSAT',
        'start_time_gmt': 1585994946.924365,
        'diff': 'solution1.txt'
    },
    'challenge2': {
        'trackasat_lat': 51.43,
        'trackasat_long': 5.5,
        'satellite_name': 'GLOBALSTAR M094',
        'start_time_gmt': 1586418067.298839,
        'diff': 'solution2.txt'
    },
    'challenge3': {
        'trackasat_lat': 8.4333,
        'trackasat_long': -82.4333,
        'satellite_name': 'GLOBALSTAR M089',
        'start_time_gmt': 1586329975.737949,
        'diff': 'solution3.txt'
    },
    'challenge4': {
        'trackasat_lat': -20.0013,
        'trackasat_long': 148.2087,
        'satellite_name': 'GLOBALSTAR M089',
        'start_time_gmt': 1586944476.246937,
        'diff': 'solution4.txt'
    },
    'live': {
        'trackasat_lat': 54.2,
        'trackasat_long': 37.6299,
        'satellite_name': 'COSMOS 2509',
        'start_time_gmt': 1586108314.10513,
        'diff': None
    }
}

@click.command()
@click.argument('challenge')
def run(challenge):
    '''
    CHALLENGE:\n
        [challenge0, challenge1, challenge2, challenge3, challenge4, live]
    '''
    if challenge not in CHALLENGES:
        print('invalid challenge')
        return
    challenge = CHALLENGES[challenge]
    found_sat = None
    try:
        sats = load.tle_file('examples/active.txt')
        for sat in sats:
            if sat.name == challenge['satellite_name']:
                found_sat = sat
                break

        assert found_sat
        print(sat)
        print()
    except:
        print('no sat')
        sys.exit(-1)

    ts = load.timescale(builtin=True)

    trackasat = Topos(challenge['trackasat_lat'], challenge['trackasat_long'])
    difference = sat - trackasat

    current_time = datetime.fromtimestamp(
        challenge['start_time_gmt'],
        timezone.utc
    )
    final_time = current_time + timedelta(0, DURATION_SECONDS)

    t_current = ts.utc(current_time)
    topocentric = difference.at(t_current)
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

    with open(OUTPUT_FILE, 'w') as f:
        for _ in range(DURATION_SECONDS):
            t_current = ts.utc(current_time)
            topocentric = difference.at(t_current)
            elevation, current_azimuth, distance = topocentric.altaz()

            if (
                current_azimuth.degrees >= 180 and
                current_azimuth.degrees < 360
            ):
                orientation = 180        
                elevation_inverted = True
            else:
                orientation = 0
                elevation_inverted = False

            trackasat_azimuth = abs(
                (current_azimuth.degrees - orientation + 180) % 360 - 180
            )
            trackasat_azimuth_pwm = (trackasat_azimuth * 4915 / 180) + 2457

            if elevation_inverted:
                trackasat_elevation_pwm = \
                    (4915 * (180 - elevation.degrees) / 180) + 2457
            else:
                trackasat_elevation_pwm = \
                    (4915 * elevation.degrees / 180) + 2457

            f.write(
                str(current_time.timestamp()) + ', '+
                str(int(trackasat_azimuth_pwm)) + ', ' +
                str(int(trackasat_elevation_pwm)) + '\n'
            )

            current_time = current_time + timedelta(0, 1)

        f.write('\n\n')
        print('\nwrote', OUTPUT_FILE)
        f.close()

    diff = challenge['diff']
    if diff:
        print()

        diff_string = EXAMPLES_FOLDER + '/' + diff + ' ' + OUTPUT_FILE
        print('diff', diff_string)
        print('vimdiff', diff_string)

if __name__ == '__main__':
    run()
