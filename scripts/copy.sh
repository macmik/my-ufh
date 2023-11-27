rsync -avr --exclude "*.db" --exclude "*venv*" --exclude ".git*" --exclude ".idea" --exclude ".db" --exclude "*pyc" --exclude "*json" ../ pi@192.168.68.117:/home/pi/my-ufh
