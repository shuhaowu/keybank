# -*- mode: ruby -*-
# vi: set ft=ruby :

$script = <<SCRIPT
sudo apt-get install -y git
git config --global user.name 'John Doe'
git config --global user.email 'john@example.com'
cp /root/.gitconfig /home/vagrant/.gitconfig
chown vagrant:vagrant /home/vagrant/.gitconfig
SCRIPT

Vagrant.configure(2) do |config|
  config.vm.box = "ubuntu/trusty64"

  config.vm.provision "shell", inline: $script
end
