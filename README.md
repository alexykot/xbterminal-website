# README

## Development

Requirements:

* Python 2
* VirtualBox
* vagrant
* vagrant-triggers plugin
* fabric (optional)

### Run vagrant

Edit `vagrant/settings.yml` (see [example](vagrant/default_settings.yml)).

Start VM:

```
vagrant up
```

### Certificates

Put necessary certificates into `certs` directory.

### Local settings

Create local settings file:

```
cp config/settings_vagrant.py.dist xbterminal/xbterminal/local_settings.py
```

### Start server

```
vagrant ssh
. venv/bin/activate
cd /vagrant
python xbterminal/manage.py migrate
honcho start
```
