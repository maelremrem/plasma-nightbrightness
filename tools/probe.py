#!/usr/bin/env python3
"""Read PowerDevil D-Bus display state and optionally test a reversible write."""
import argparse
import shutil
import subprocess
import time

SERVICE = 'org.kde.ScreenBrightness'
INTERFACE = 'org.kde.ScreenBrightness.Display'

def main():
    parser = argparse.ArgumentParser(description='Plasma brightness capability test')
    parser.add_argument('--display', default='display0')
    parser.add_argument('--write-test', action='store_true', help='Try a 3 percent change, then restore')
    args = parser.parse_args()
    exe = shutil.which('qdbus-qt6') or shutil.which('qdbus6')
    if exe is None:
        parser.error('qdbus-qt6 missing: sudo dnf install qt6-qttools')
    path = f'/org/kde/ScreenBrightness/{args.display}'

    def call(method, *params):
        result = subprocess.run([exe, SERVICE, path, INTERFACE + '.' + method,
                                 *(str(x) for x in params)], check=True,
                                capture_output=True, text=True, timeout=12)
        return result.stdout.strip()

    maximum = int(call('MaxBrightness'))
    current = int(call('Brightness'))
    if maximum <= 0:
        parser.error('Invalid maximum brightness')
    print(f'{args.display}: brightness={current}/{maximum} ({current * 100 / maximum:.1f}%)')
    if not args.write_test:
        print('Read-only test OK. Use --write-test to verify the setter.')
        return
    offset = max(1, round(maximum * 0.03))
    temporary = current - offset if current > offset else min(maximum, current + offset)
    print(f'Testing temporary {temporary * 100 / maximum:.1f}% ...')
    try:
        call('SetBrightness', temporary, 1)
        time.sleep(2)
        after = int(call('Brightness'))
        print('Observed:', after)
        if abs(after - temporary) > max(2, round(maximum * 0.02)):
            print('Warning: monitor did not reach the requested brightness')
    finally:
        call('SetBrightness', current, 1)
        print('Original brightness restored')

if __name__ == '__main__':
    main()
