ls
ls
passwd
ls
git clone git@github.com:NVlabs/timeloop.git
ls
cd maestro
ls
cd ..
ls
cd timeloop
ls
cd ..
cd timeloop-accelergy-exercises/
ls
cd /home/esp2026/kl3755/maestro
ls
scons
sudo apt install scons
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
cd /home/esp2026/kl3755/maestro
scons
cd /home/esp2026/kl3755
./compare/maestro/run_maestro.sh
ls
./compare/maestro/run_maestro.sh
./compare/run_all.sh
python3 compare/parse_maestro.py
./compare/timeloop/run_timeloop.sh
python3 compare/parse_timeloop.py
python3 compare/plot_results.py
./compare/run_all.sh
ls compare/results/
ls
cd /home/esp2026/kl3755
pip install scons --user
export PATH="$HOME/.local/bin:$PATH"
cd maestro
scons
cd ..
ls
chmod +x compare/maestro/run_maestro.sh
./compare/maestro/run_maestro.sh
python3 compare/parse_maestro.py
chmod +x compare/timeloop/run_timeloop.sh
./compare/timeloop/run_timeloop.sh
python3 compare/parse_timeloop.py
pip install matplotlib --user
python3 compare/plot_results.py
cd /home/esp2026/kl3755
./compare/maestro/run_maestro.sh
cd /home/esp2026/kl3755/maestro
./maestro   --HW_file='/home/esp2026/kl3755/compare/maestro/hw/accelerator_1.m'   --Mapping_file='/home/esp2026/kl3755/compare/maestro/mapping/single_layer_rs_eyeriss.m'   --print_res=true --print_res_csv_file=true --print_log_file=false
cd /home/esp2026/kl3755/maestro
./maestro   --HW_file='/home/esp2026/kl3755/compare/maestro/hw/accelerator_1.m'   --Mapping_file='/home/esp2026/kl3755/compare/maestro/mapping/single_layer_rs_eyeriss.m'   --print_res=true --print_res_csv_file=true --print_log_file=false
cd /home/esp2026/kl3755
./compare/maestro/run_maestro.sh
python3 compare/parse_maestro.py
python3 compare/plot_results.py
./compare/maestro/run_maestro.sh
python3 compare/parse_maestro.py
python3 compare/plot_results.py
./maestro/maestro --HW_file='compare/maestro/hw/accelerator_1.m'                   --Mapping_file='compare/maestro/mapping/single_layer_os_shidiannao.m'                   --print_res=true --print_res_csv_file=true --print_log_file=false
ls
chmod +x compare/timeloop/run_timeloop_same_layer_rs.sh
./compare/timeloop/run_timeloop_same_layer_rs.sh
pip install pytimeloop
pip install --user pytimeloop
chmod +x compare/timeloop/run_timeloop_same_layer_rs_docker.sh
./compare/timeloop/run_timeloop_same_layer_rs_docker.sh
sudo apt-get update && sudo apt-get install -y docker.io
docker pull timeloopaccelergy/timeloop-accelergy-pytorch:latest-amd64
https://docs.docker.com/engine/install/
./compare/timeloop/run_timeloop_same_layer_rs_docker.sh
sudo apt-get update && sudo apt-get install -y docker.io
sudo usermod -aG docker $USER
ls
sudo apt-get update
ls
cd /home/esp2026/kl3755
git init
git add .
git commit -m "Initial commit: MAESTRO/Timeloop dataflow comparison"
cd /home/esp2026/kl3755
git config user.name "Your Name"
git config user.name "Kevin Liu"
git config user.email "kl3755@colubmia.edu"
git commit -m "Initial commit: MAESTRO/Timeloop dataflow comparison"
cd /home/esp2026/kl3755
git remote add origin git@github.com:kevinliu0402/system-level-accelerator.git
git status
git branch -M main
git push -u origin main
cd /home/esp2026/kl3755
git remote set-url origin https://github.com/kevinliu0402/system-level-accelerator.git
git push -u origin main
cd /home/esp2026/kl3755
git remote set-url origin https://github.com/kevinliu0402/system-level-accelerator.git
git config --global --unset credential.helper 2>/dev/null || true
git config --unset credential.helper 2>/dev/null || true
unset GIT_ASKPASS
# 3. Push again
git push -u origin main
cd /home/esp2026/kl3755
git config --global --unset credential.helper 2>/dev/null || true
git config --unset credential.helper 2>/dev/null || true
unset GIT_ASKPASS
git push -u origin main
git config --global --unset credential.helper 2>/dev/null || true
git config --unset credential.helper 2>/dev/null || true
unset GIT_ASKPASS
git remote set-url origin https://github.com/kevinliu0402/system-level-accelerator.git
git remote -v    # should show that URL
git push -u origin main
cd /home/esp2026/kl3755
rm -rf .git
git init
cat > .gitignore << 'EOF'
# IDE / Cursor / tooling

.cursor/
.cursor-server/
.vscode/

# External tool repos (huge)

maestro/
timeloop/
timeloop-accelergy-exercises/

# Python cache

__pycache__/
*.pyc
EOF

git add .gitignore
git add README.md
git add compare
git add docs
git commit -m "Initial commit: MAESTRO/Timeloop dataflow comparison"
git remote add origin https://github.com/kevinliu0402/system-level-accelerator.git
git branch -M main
git push -u origin main
cd /home/esp2026/kl3755
git status
git commit -m "Initial commit: MAESTRO/Timeloop dataflow comparison"
git config --global user.email kl3755@columbia.edu
git config --global user.name Kevin Liu
git commit -m "Initial commit: MAESTRO/Timeloop dataflow comparison"
git branch -M main
git remote add origin https://github.com/kevinliu0402/system-level-accelerator.git  # or skip if already added
git push -u origin main
ls
cd /home/esp2026/kl3755
mv maestro maestro_local_backup
mv timeloop timeloop_local_backup
mv timeloop-accelergy-exercises timeloop-accelergy-exercises_local_backup
git submodule add https://github.com/maestro-project/maestro.git maestro
git submodule add https://github.com/NVlabs/timeloop.git timeloop
git submodule add https://github.com/Accelergy-Project/timeloop-accelergy-exercises.git timeloop-accelergy-exercises
git status
git add .gitmodules .gitignore maestro timeloop timeloop-accelergy-exercises
git commit -m "Add maestro, timeloop, timeloop-accelergy-exercises as submodules"
git push -u origin main
git config --global --unset credential.helper 2>/dev/null || true
git config --unset credential.helper 2>/dev/null || true
unset GIT_ASKPASS
git remote set-url origin https://github.com/kevinliu0402/system-level-accelerator.git
git remote -v
git push -u origin main
ls
docker pull timeloopaccelergy/timeloop-accelergy-pytorch:latest-amd64
l;s
ls
docker pull timeloopaccelergy/timeloop-accelergy-pytorch:latest-amd64
sudo usermod -aG docker kl3755
sudo docker pull timeloopaccelergy/timeloop-accelergy-pytorch:latest-amd64
ls
docker pull timeloopaccelergy/timeloop-accelergy-pytorch:latest-amd64
ls
./compare/timeloop/run_timeloop.sh
python3 compare/parse_timeloop.py && python3 compare/plot_results.py
./compare/timeloop/run_timeloop.sh
python3 compare/parse_timeloop.py && python3 compare/plot_results.py
./compare/timeloop/run_timeloop.sh
sudo usermod -aG docker $USER
. "/home/esp2026/kl3755/.cursor-server/bin/linux-x64/7d96c2a03bb088ad367615e9da1a3fe20fbbc6a0/out/vs/workbench/contrib/terminal/common/scripts/shellIntegration-bash.sh"
ls
./compare/timeloop/run_timeloop.sh
docker run --help
groups
ls
exit
newgrp docker
groups
docker pull timeloopaccelergy/timeloop-accelergy-pytorch:latest-amd64
docker pull timeloopaccelergy/timeloop-accelergy-pytorch:latest-amd64./compare/timeloop/
./compare/timeloop/run_timeloop.sh
python3 compare/parse_timeloop.py && python3 compare/plot_results.py
cd /home/esp2026/kl3755
./compare/timeloop/run_timeloop.sh
python3 compare/parse_timeloop.py && python3 compare/plot_results.py
cd /home/esp2026/kl3755
./compare/timeloop/run_timeloop.sh
python3 compare/parse_timeloop.py && python3 compare/plot_results.py
./compare/timeloop/run_timeloop.sh
python3 compare/parse_timeloop.py && python3 compare/plot_results.py
./compare/timeloop/run_timeloop.sh
python3 compare/parse_timeloop.py && python3 compare/plot_results.py
./compare/timeloop/run_timeloop.sh
python3 compare/parse_timeloop.py && python3 compare/plot_results.py
./compare/timeloop/run_timeloop.sh
python3 compare/parse_timeloop.py && python3 compare/plot_results.py
ls
git status
git commit -m "0308"
git push
cd /home/esp2026/kl3755
git remote set-url origin git@github.com:kevinliu0402/system-level-accelerator.git
git push
git status
git push
git status
ls 
cd maestro
ls
python3 compare/parse_maestro.py
cd ..
python3 compare/parse_maestro.py
python3 compare/parse_maestro.py && python3 compare/parse_timeloop.py && python3 compare/plot_results.py
ls
./compare/timeloop/run_timeloop_same_layer_rs_docker.sh
cd /home/esp2026/kl3755
./compare/timeloop/run_timeloop_same_layer_rs_docker.sh
mv compare/results/timeloop_rs_eyeriss.stats.txt.bak compare/results/timeloop_rs_eyeriss.stats.txt
python3 compare/parse_timeloop.py
cd /home/esp2026/kl3755/system-level-accelerator
mv /home/esp2026/kl3755/compare/results/timeloop_rs_eyeriss.stats.txt.bak    /home/esp2026/kl3755/compare/results/timeloop_rs_eyeriss.stats.txt
python3 /home/esp2026/kl3755/compare/parse_timeloop.py
python3 /home/esp2026/kl3755/compare/plot_results.py
cd ..
ls
cd kl375
cd kl3755
git checkout HEAD -- compare/timeloop compare/parse_timeloop.py
./compare/timeloop/run_timeloop.sh
docker pull timeloopaccelergy/timeloop-accelergy-pytorch:latest-amd64
docker run --rm -it   -v /home/esp2026/kl3755:/home/repo   -w /home/repo   timeloopaccelergy/timeloop-accelergy-pytorch:latest-amd64   bash
git status
python3 compare/plot_results.py
git status
git commit -m "0311"
git push
git checkout -b update-comparison
git push -u origin update-comparison
git status
ls
ls docs
cd /home/esp2026/kl3755/docs
ls
/home/esp2026/kl3755/docs/midterm_presentation.md
ls
