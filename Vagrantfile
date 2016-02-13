require 'yaml'

VAGRANTFILE_API_VERSION = "2"

settings = YAML::load_file("vagrant/default_settings.yml")
begin
  settings.merge!(YAML::load_file("vagrant/settings.yml"))
rescue Errno::ENOENT
end

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

  config.vm.box = "ubuntu/trusty64"
  config.vm.hostname = "xbt-server-dev"

  config.vm.network "forwarded_port", guest: 5432, host: settings['vm']['ports']['postgresql']
  config.vm.network "forwarded_port", guest: 6379, host: settings['vm']['ports']['redis']
  config.vm.network "forwarded_port", guest: 18332, host: settings['vm']['ports']['bitcoind']

  config.vm.provider "virtualbox" do |vb|
    vb.name = "XBTerminal Server"
    vb.memory = settings['vm']['memory']
    vb.cpus = settings['vm']['cpus']
  end

  config.vbguest.auto_update = false

  config.vm.synced_folder "vagrant/salt/roots/", "/srv/"

  config.vm.provision :salt do |salt|
    salt.masterless = true
    salt.minion_config = "vagrant/salt/minion.conf"
    salt.run_highstate = true
    salt.verbose = true

    salt.pillar(settings['pillar'])
  end

end
