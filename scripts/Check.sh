if [ $(pgrep -cf Run.sh) -gt 0 ]; then
    tmux new -As Skycast
else
    tmux new -As Skycast \; send-keys "uv run --with \"prawcore>=3.0.1\" skycast.py" Enter
fi