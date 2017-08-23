# Shp2PgsqlGUI for mac
Run shp2pgsql in GUI mode. [shp2pgsql](http://www.bostongis.com/pgsql2shp_shp2pgsql_quickguide.bqg) command line interface is required

![Shp2PgsqlGUI v0.2](/screenshot.png?raw=true "Shp2PgsqlGUI v0.2")

### Installation
- Install postgis bundle using [Homebrew](https://brew.sh/). This bundle contains [shp2pgsql](http://www.bostongis.com/pgsql2shp_shp2pgsql_quickguide.bqg) cli

```bash
brew install postgis
```

- Run the application


### Build requirements
- [Python](https://www.python.org/)
- [PyQt 5](https://pypi.python.org/pypi/PyQt5)
- [PyInstaller](http://www.pyinstaller.org/)
- [PyCrypto](https://pypi.python.org/pypi/pycrypto/)

### Building
- Run this code from project directory

```bash
pyinstaller -w --osx-bundle-identifier=com.your.identifier --key=your-encryption-key -i pgAdmin4.icns Shp2PgsqlGUI.py
```
