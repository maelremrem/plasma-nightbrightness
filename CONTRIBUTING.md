# Contributing

This is an experimental community project targeting Fedora 44 and KDE Plasma 6.

Please search for existing issues before opening a new one. For bugs, include your Plasma, Qt and Fedora versions, relevant `journalctl --user -u nightbrightness.service` logs, and whether the monitor brightness probe works. Redact any private coordinates, paths, or personal data.

Before proposing a pull request, run:

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile daemon/nightbrightness.py tools/probe.py
bash -n build-rpm.sh
```

Code comments and contributions should be in English. The current interface is primarily French; internationalization work is welcome.
