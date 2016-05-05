# -*- mode: ruby -*-
# vi: set ft=ruby :

$script = <<SCRIPT
# General setup
apt-get install -y git python3 python3-pip python3-dev language-pack-en
pip3 install -r /vagrant/requirements.txt
SCRIPT

Vagrant.configure(2) do |config|
  config.vm.box = "ubuntu/trusty64"

  config.vm.provision "shell", inline: $script
  config.vm.synced_folder ".", "/vagrant"

  config.vm.provider :virtualbox do |vb|
    vb.customize ["modifyvm", :id, "--nictype1", "virtio"]
  end
end
