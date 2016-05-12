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

### Local settings

These variables should be redefined in `xbterminal/xbterminal/local_settings.py`:

* SITE_ID
* CACHES - cache settings
* RQ_QUEUES - redis queue settings
* EMAIL_* - SMTP server settings
* PKI_KEY_FILE, PKI_CERTIFICATES - certificates for BIP70
* BITCOIND_SERVERS - bitcoind settings
* RECAPTCHA_* - reCaptcha settings
* SALT_SERVERS - Salt server settings
* APTLY_SERVERS - Aptly server settings

### Start server

```
vagrant ssh
. venv/bin/activate
cd /vagrant
python xbterminal/manage.py migrate
honcho start
```
