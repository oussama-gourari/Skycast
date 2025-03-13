if [ $(pgrep -f Run.sh) ]; then
    tmux new -As Skycast
else
    tmux new -As Skycast \; send-keys "bash Space Run KP. sh" Enter
fi