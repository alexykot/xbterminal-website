require 'yaml'

Vagrant.configure("2") do |config|
  settings = YAML::load_file("vagrant/default_settings.yml")
  begin
    settings.merge!(YAML::load_file("vagrant/settings.yml"))
  rescue Errno::ENOENT
  end

  config.vm.box = "ubuntu/trusty64"
  config.vm.hostname = "xbt-server-dev"

  config.vm.network "forwarded_port", guest: 5432, host: settings['vm']['ports']['postgresql']
  config.vm.network "forwarded_port", guest: 6379, host: settings['vm']['ports']['redis']
  config.vm.network "forwarded_port", guest: 18332, host: settings['vm']['ports']['bitcoind']
  config.vm.network "forwarded_port", guest: 8083, host: settings['vm']['ports']['xbt-server']

  config.vm.provider "virtualbox" do |vb|
    vb.name = "XBTerminal Server"
    vb.memory = settings['vm']['memory']
    vb.cpus = settings['vm']['cpus']
  end

  config.vm.provision "fix-no-tty", type: "shell" do |sh|
    sh.privileged = false
    sh.inline = "sudo sed -i '/tty/!s/mesg n/tty -s \\&\\& mesg n/' /root/.profile"
  end

  config.vm.synced_folder "vagrant/salt/roots/", "/srv/"

  config.vm.provision :salt do |salt|
    salt.masterless = true
    salt.minion_config = "vagrant/salt/minion.conf"
    salt.run_highstate = true
    salt.verbose = true

    salt.pillar(settings['pillar'])
  end

  config.trigger.before :halt do
    run_remote "bash /vagrant/vagrant/backup.sh"
  end

end
