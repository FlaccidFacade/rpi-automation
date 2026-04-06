#!/bin/bash
# This script runs once on first boot, then removes itself.
# Edit the values below to match your setup.

set -o errexit
set -o nounset

HOSTNAME="raspberrypi"
LOCALE="en_US.UTF-8"
KEYBOARD="us"
TIMEZONE="UTC"

# --- Set hostname ---
CURRENT_HOSTNAME=$(cat /etc/hostname | tr -d " \t\n\r")
if [ -f /usr/lib/raspberrypi-sys-mods/imager_custom ]; then
    /usr/lib/raspberrypi-sys-mods/imager_custom set_hostname "$HOSTNAME"
else
    echo "$HOSTNAME" >/etc/hostname
    sed -i "s/127.0.1.1.*$CURRENT_HOSTNAME/127.0.1.1\t$HOSTNAME/g" /etc/hosts
fi

# --- Set locale ---
if [ -f /usr/lib/raspberrypi-sys-mods/imager_custom ]; then
    /usr/lib/raspberrypi-sys-mods/imager_custom set_locale "$LOCALE" "$KEYBOARD"
else
    if [ -f /etc/default/locale ]; then
        sed -i "s/LANG=.*/LANG=$LOCALE/" /etc/default/locale
    else
        echo "LANG=$LOCALE" >/etc/default/locale
    fi
fi

# --- Set timezone ---
rm -f /etc/localtime
echo "$TIMEZONE" >/etc/timezone
dpkg-reconfigure -f noninteractive tzdata


# --- Set Aliases ---
# Create /etc/profile.d/custom_aliases.sh
cat > /etc/profile.d/custom_aliases.sh << 'EOF'
alias l='ls -al --color=auto --no-group --time-style=long-iso --group-directories-first'
alias gs='git status'
alias ga='git add'
alias gc='git commit'
alias gp='git push'
alias gf='git fetch'
alias gl='git log --oneline --graph --decorate'
alias d='docker'
alias dc='docker-compose'
alias py='python3'
alias py3='python3'
alias py2='python2'
alias v='vim'

alias ..='cd ..'
EOF
chmod +x /etc/profile.d/custom_aliases.sh


# --- Install git ---
echo "Installing git..."
apt-get update
apt-get install -y git
git config --global alias.s status
git config --global alias.a add
git config --global alias.c commit
git config --global alias.p push
git config --global alias.f fetch
git config --global alias.l "log --oneline --graph --decorate"

# --- Install Docker ---
echo "Installing Docker..."
apt-get install -y docker.io
systemctl enable docker
systemctl start docker 

# --- Install Docker Compose ---

echo "Installing Docker Compose..."
DOCKER_COMPOSE_VERSION="2.30.2"
curl -L "https://github.com/docker/compose/releases/download/v$DOCKER_COMPOSE_VERSION/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# --- Install Python ---
echo "Installing Python..."
apt-get install -y python3 python3-pip python3-venv
ln -s /usr/bin/python3 /usr/bin/python
ln -s /usr/bin/pip3 /usr/bin/pip        

# --- Install Vim ---
echo "Installing Vim..."
apt-get install -y vim

# --- Install Github CLI ---
echo "Installing GitHub CLI..."
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null
apt update
apt install -y gh       

# Create a minimal system-wide vimrc
cat > /etc/vim/vimrc << 'EOF'
" Minimal system-wide vim settings
set nocompatible
set number
set relativenumber
set showcmd
set cursorline
set expandtab
set tabstop=4
set shiftwidth=4
set softtabstop=4
set autoindent
set smartindent
set nowrap
set incsearch
set hlsearch
set ignorecase
set smartcase
syntax on
if has("mouse")
  set mouse=a
endif
EOF



# --- Clean up ---
CMDLINE=/boot/firmware/cmdline.txt
if [ -f "$CMDLINE" ]; then
    sed -i 's|[[:space:]]\+systemd.run=[^[:space:]]\+||g' "$CMDLINE"
fi
rm -f /boot/firmware/firstrun.sh
exit 0
