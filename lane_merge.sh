#! /bin/bash

gnome-terminal --tab --title="vanetza" \
--working-directory='/media/tiagoadonis/Disco Dados/Universidade/MIECT/5º Ano/2º Semestre/Cadeiras/RSA/Proj/lane_merge/vanetza' \
-- /bin/bash -c "sudo docker-compose up; exec /bin/bash" 

sleep 6

gnome-terminal --tab --title="app.py" \
--working-directory='/media/tiagoadonis/Disco Dados/Universidade/MIECT/5º Ano/2º Semestre/Cadeiras/RSA/Proj/lane_merge/Lane_Merge_v1/app' \
-- /bin/bash -c "python3 app.py; exec /bin/bash" 

sleep 1

gnome-terminal --tab --title="Web App" \
--working-directory='/home/tiagoadonis/' -- /bin/bash -c "google-chrome http://127.0.0.1:5000; exec /bin/bash" 