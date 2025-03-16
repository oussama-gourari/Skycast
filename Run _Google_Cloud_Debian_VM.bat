@echo off
SETLOCAL ENABLEEXTENSIONS

set SSH_KEY_FILENAME=
set VM_USERNAME=
set VM_EXTERNAL_IP=

TITLE Skycast ^| Google Cloud Debian VM

set FILE_PATH=%USERPROFILE%\.ssh\%SSH_KEY_FILENAME%
set USER_AT_HOST=%VM_USERNAME%@%VM_EXTERNAL_IP%
set TMUX_SESSION=Skycast
set UPDATE_SKYCAST=0

set /P UPDATE=Do you want to update Skycast on the VM? (Y/N, default is N): 
IF /I "%UPDATE%" EQU "Y" (
    set UPDATE_SKYCAST=1
    echo Updating Skycast from the GitHub repository.
) ELSE (
    echo Skipping updating Skycast.
)

ssh -i "%FILE_PATH%" %USER_AT_HOST% -t "which tmux; if [ $? -ne 0 ]; then sudo apt install tmux; fi; which git; if [ $? -ne 0 ]; then sudo apt install git; fi; if [ %UPDATE_SKYCAST% -eq 1 ]; then rm -rf Skycast; fi; git clone https://github.com/oussama-gourari/Skycast.git"
scp -i "%FILE_PATH%" src/config.py %USER_AT_HOST%:Skycast/src/
CLS
ssh -i "%FILE_PATH%" %USER_AT_HOST% -t "cd Skycast; if [ $(pgrep -cf skycast.py) -gt 1 ]; then tmux attach -t %TMUX_SESSION%; else tmux kill-session -t %TMUX_SESSION%; tmux new -s %TMUX_SESSION% \; send-keys "bash Space Run_Linux" Enter; fi"
scp -i "%FILE_PATH%" %USER_AT_HOST%:Skycast/logs/log.log logs/log_vm.log

ENDLOCAL
PAUSE
