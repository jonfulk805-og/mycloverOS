# ~/.bashrc -- mycloverOS default shell config

# If not running interactively, don't do anything
case $- in
    *i*) ;;
      *) return;;
esac

# History
HISTCONTROL=ignoreboth
HISTSIZE=10000
HISTFILESIZE=20000
shopt -s histappend

# Window size
shopt -s checkwinsize

# Colors
alias ls='ls --color=auto'
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'
alias grep='grep --color=auto'

# mycloverOS shortcuts
alias cs='sudo cloverstack-ctl'
alias cs-status='sudo cloverstack-ctl status'
alias cs-logs='sudo cloverstack-ctl logs'
alias update='sudo myclover-update'

# Prompt
if [[ $(id -u) -eq 0 ]]; then
    PS1='\[\033[0;31m\][mycloverOS]\[\033[0m\] \w # '
else
    PS1='\[\033[0;32m\][mycloverOS]\[\033[0m\] \w $ '
fi

# CloverStack environment
export CLOVERSTACK_ROOT="/opt/cloverstack"
export PATH="${PATH}:/usr/local/bin"

echo ""
echo "  mycloverOS $(cat /etc/myclover/release 2>/dev/null | grep DISTRO_VERSION | cut -d= -f2 | tr -d '\"' || echo '')"
echo "  Type 'cs-status' to see CloverStack module status"
echo ""
