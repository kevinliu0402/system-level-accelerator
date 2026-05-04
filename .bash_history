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
Add NoCand shared DRAM models
cd /home/esp2026/kl3755
python3 compare/system_model/run_example.py
python3 -c "
from compare.system_model.noc_dram import AcceleratorTile, SystemConfig, estimate_multi_accelerator_system
tiles = [
    AcceleratorTile('tile0', latency_cycles=451584,
        dram_bytes_read=1e8, dram_bytes_write=5e7,
        noc_bytes_to_dram=1.5e8, noc_bytes_to_peer=0),
]
cfg = SystemConfig(clock_hz=1e9, dram_bandwidth_gbps=25, noc_bandwidth_gbps=100)
e = estimate_multi_accelerator_system(tiles, cfg)
print(e)
"
python3 compare/plot_results.py
python3 compare/system_model/run_example.py
git status
git add -a
git add -A
git status
git commit -m "0323"
git push -u origin main
git checkout -b update-comparison
git push -u origin update-comparison
git status
ls
python3 compare/system_model/run_example.py
ls
cd ..
ls
cd ..
ls
cd ..
ls
git clone git@github.com:CSEE4340-26/p4.UNI.git
ls
cd p4.UNI
cd ..
ls
git clone git@github.com:CSEE4340-26/p4.UNI.git
ls
cd p4.UNI/
ls
git status
git add verilog/sys_defs.svh 
git add test/rob_test.sv 
git add verilog/rob.sv 
git status
git checkout submission
git commit -m "0325"
git checkout submission
git status
git commit "0325"
git commit -m "0325"
git push -u origin submission
cd /home/esp2026/kl3755
git status -sb
git diff --cached --name-only
git diff --cached --stat
git diff --cached --name-only
git commit -m "Add ROB + commit logic for Milestone 2"
git push -u origin submission
cd /home/esp2026/kl3755
git log -1 --oneline
git branch -r
git status
cd /home/esp2026/kl3755
git add p4.UNI/verilog/sys_defs.svh
git status -sb
git push
ls
git p4.UNI/
cd p4.UNI/
ls
git clone git@github.com:CSEE4340-26/p4.UNI.git
ls
git status -sb
git diff --cached --name-only
git commit -m "Update sys_defs parameters for Milestone 2"
cd ..
ls
cd p4.UNI/
ls
git status
cd ..
ls
git clone git@github.com:CSEE4340-26/p4.UNI.git
ls
cd p4.UNI/
ls
git status
git checkout submission
cd /home/esp2026/kl3755/p4.UNI
git status -sb
git stash push -u -m "WIP before switching to submission"
git checkout -b submission origin/submission
git status
git add test/rob_test.sv 
git add verilog/rob.sv 
git commit -m "0325"
git add verilog/sys_defs.svh 
git status
git push
ls
cd p4.UNI/
ls
git pull
git status
git add Makefile verilog/rename_iq_top.sv pdfs/4340eecs_proposal.pdf verilog/rob_2wide.sv 
git commit -m "0326"
git push
git status
ls
python3 compare/system_model/run_bw_combos.py
git status
ls
git add compare/system_model/magma_bw_allocator.py compare/system_model/run_bw_combos.py 
git commit -m "0330"
git push
python3 compare/system_model/run_bw_combos.py
git status
git add compare/system_model/run_bw_combos.py 
git commit -m "0330 maestro DRAM allocator"
git push
git add compare/system_model/run_bw_combos.py 
python3 compare/system_model/run_bw_combos.py
ls
lls
ls
mkdir 4840
ls
cd 4840
ls
cd lab3/
ls
qsys-edit soc_system.qsys
cd lab3-hw\ 2/
ls
qsys-edit soc_system.qsys
cd ..
ls
cd..
cd ..
ls
cd usr
ls
cd ..
ls
cd tmp
ls
cd ..
ls
cd ..
ls
cd ..
cd home 
ls
cd esp2026
ls
cd kl3755
ls
python3 compare/system_model/run_bw_combos.py
ls
cd 6868/
ls
./maestro --HW_file=data/hw/accelerator_1.m --Mapping_file=data/mapping/Resnet50_yxp_os.m --print_res_csv_file=true
cd /home/esp2026/kl3755/6868/maestro
./maestro --HW_file='data/hw/accelerator_1.m'  --Mapping_file='data/mapping/Resnet50_yxp_os.m'   --print_res=false --print_res_csv_file=true --print_log_file=false
cp Resnet50_yxp_os.csv tools/jupyter_notebook/data/Resnet50_yxp_os_pe256.csv
cd /home/esp2026/kl3755/6868 && python3 compare/system_model/run_bw_combos.py
cd /home/esp2026/kl3755/6868 && BW_LAYER=CONV3_1_2 python3 compare/system_model/run_bw_combos.py
cd /home/esp2026/kl3755/6868 && SYSTEM_BW=256 BW_LAYER=CONV2_1_2 python3 compare/system_model/run_bw_combos.py
cd /home/esp2026/kl3755/6868/maestro && ./maestro --HW_file='data/hw/accelerator_1.m' --Mapping_file='data/mapping/Resnet50_yxp_os.m' --print_res=false --print_res_csv_file=true --print_log_file=false && cp Resnet50_yxp_os.csv tools/jupyter_notebook/data/Resnet50_yxp_os_pe256.csv
cd ..
git status
cd ..
cd 6868
git push
git commit -m "0405"
cd /home/esp2026/kl3755
git add compare/ docs/ maestro maestro_local_backup timeloop timeloop-accelergy-exercises timeloop-accelergy-exercises_local_backup timeloop_local_backup
cd /home/esp2026/kl3755
git add -u compare docs maestro maestro_local_backup timeloop timeloop-accelergy-exercises timeloop-accelergy-exercises_local_backup timeloop_local_backup
ls
cd 6868
ls
cd ~/6868
git rev-parse --show-toplevel   # should print .../6868 if this is the repo root
cd /home/esp2026/kl3755
git add 6868/compare 6868/docs 6868/maestro 6868/maestro_local_backup         6868/timeloop 6868/timeloop-accelergy-exercises         6868/timeloop-accelergy-exercises_local_backup 6868/timeloop_local_backup
(Adjust names if anything differs; git st; d; :wq exit
cd /home/esp2026/kl3755
git add -u compare docs maestro maestro_local_backup timeloop         timeloop-accelergy-exercises timeloop-accelergy-exercises_local_backup timeloop_local_backup
ls
cd /home/esp2026/kl3755
pwd
git status -sb
git ls-files | grep -E '^compare/|^6868/compare/' | head
cd /home/esp2026/kl3755
git add -u 6868/compare 6868/docs 6868/maestro 6868/maestro_local_backup         6868/timeloop 6868/timeloop-accelergy-exercises         6868/timeloop-accelergy-exercises_local_backup 6868/timeloop_local_backup
ls
cd 6868
ls
git sstatus
git status
git commit -m "0405"
git push
git status
cd /home/esp2026/kl3755/6868_project && python3 compare/system_model/run_bw_combos.py
cd /home/esp2026/kl3755/6868_project && BW_LAYER=CONV3_1_2 SYSTEM_BW=256 python3 compare/system_model/run_bw_combos.py
cd /home/esp2026/kl3755 && git pull origin submission
git status
ls
cd 6868_project
ls
cd /home/esp2026/kl3755   # your repo root
git pull origin submission
ls
ls 6868
git status
cd /home/esp2026/kl3755 && git status -sb
cd /path/to/6868
ls
cd 6868
for L in CONV2_1_2 CONV3_1_2 CONV4_1_2; do   echo "=== BW_LAYER=$L ===";   BW_LAYER=$L python3 compare/system_model/run_bw_combos.py; done
git status
git add compare/system_model/README.md
git commit -m "0405 md"
git push
cd ..
ls
cd p4.UNI/
git status
git clone git@github.com:CSEE4340-26/p4.UNI.git
git status
git add Makefile verilog/rename_iq_top.sv verilog/rob_2wide.sv verilog/sys_defs.svh test/lsq_2wide_test.sv verilog/lsq_2wide.sv 
git status
git commit -m"0405 Kevin Liu"
git push
cd ~/p4.UNI
ls
git add   Makefile   verilog/sys_defs.svh   verilog/rob_2wide.sv   verilog/rename_iq_top.sv   verilog/lsq_2wide.sv   test/lsq_2wide_test.sv
git commit -m "Fix ROB/LSQ and Makefile (6 files)"
git pull --rebase origin submission
git push origin submission
cd ~/p4.UNI
make rob.pass              # scalar ROB
make lsq_2wide.pass        # LSQ + rob_2wide testbench
make rename_iq_top.pass    # rename + IQ + ROB glue
module avail vcs 2>/dev/null | head -20   # optional: see exact module name
module load vcs
# if that fails, try:
module load synopsys
# or whatever your cluster documents, e.g.:
# module load vcs verdi synopsys-synth
make rob.pass
make rob.pass VCS_BIN=/full/path/to/vcs
type vcs 2>/dev/null
which vcs 2>/dev/null
find /tools /opt /usr/synopsys -type f -name vcs 2>/dev/null | head -5
cd ~/p4.UNI
make rob.pass VCS_BIN=/full/path/to/vcs
ls
cd p4.UNI/
ls
git pull
make rob.pass
make rob.pass VCS_BIN=/full/path/to/vcs
make lsq_2wide.pass VCS_BIN=/full/path/to/vcs
find /tools /opt /usr/synopsys /apps -type f -name vcs 2>/dev/null | head -10
which vcs
ls
cd 6868
python3 compare/system_model/run_scar_multi_model_bw.py
SCAR_SCENARIO=DC_A SYSTEM_BW=256 python3 compare/system_model/run_scar_multi_model_bw.py
python3 compare/system_model/run_scar_multi_model_bw.py
SCAR_SCENARIO=DC_A SYSTEM_BW=256 python3 compare/system_model/run_scar_multi_model_bw.py
SCAR_OUT_CSV=compare/results/scar_multi_model_bw.csv   python3 compare/system_model/run_scar_multi_model_bw.py
python3 compare/system_model/run_bw_combos.py
BW_LAYER=CONV3_1_2 SYSTEM_BW=100 python3 compare/system_model/run_bw_combos.py
python3 compare/system_model/run_example.py
python3 compare/system_model/run_bw_combos.py
BW_LAYER=CONV3_1_2 python3 compare/system_model/run_bw_combos.py
SYSTEM_BW=256 python3 compare/system_model/run_bw_combos.py
git status
git add compare/system_model/README.md docs/SYSTEM_LEVEL_MODEL.md 
git add compare/results/scar_multi_model_bw.csv
git add compare/system_model/maestro_layer_metrics.py 
git add compare/system_model/run_scar_multi_model_bw.py 
git add compare/system_model/scar_workloads.json 
git commit -m "0406 SCAR"
git push
ls
cd 6868/
ls
pip install torch torchvision
cd /path/to/6868
python3 compare/scripts/export_resnet_mobilenet_onnx.py
pip install --user onnx
pip install onnx
cd ~/6868 && python3 compare/scripts/export_resnet_mobilenet_onnx.py
python3 compare/system_model/run_bw_combos_full_network.py
python3 compare/system_model/run_mobilenet_full_network_bw.py
python3 compare/system_model/run_bw_combos_full_network.py
FULLNET_COMBO=RS_WS SYSTEM_BW=256 python3 compare/system_model/run_bw_combos_full_network.py
FULLNET_OUT_CSV=compare/results/full_net_bw_layers.csv   python3 compare/system_model/run_bw_combos_full_network.py
python3 compare/system_model/run_mobilenet_full_network_bw.py
FULLNET_COMBO=RS_WS SYSTEM_BW=100 python3 compare/system_model/run_mobilenet_full_network_bw.py
MOBILENET_FULLNET_OUT_CSV=compare/results/mobilenet_full_net_bw_layers.csv   python3 compare/system_model/run_mobilenet_full_network_bw.py
cd ..
pip install matplotlib
cd /path/to/6868
ls
cd 6868/
# Produce CSV then plot (ResNet-50 full net)
FULLNET_OUT_CSV=compare/results/full_net_bw_layers.csv   python3 compare/system_model/run_bw_combos_full_network.py
python3 compare/system_model/visualize_makespan.py   --csv compare/results/full_net_bw_layers.csv   --out compare/results/makespan_resnet.png
python3 compare/system_model/visualize_makespan.py   --csv compare/results/full_net_bw_layers.csv   --out compare/results/makespan_resnet_cumulative.png --cumulative
SCAR_OUT_CSV=compare/results/scar.csv   python3 compare/system_model/run_scar_multi_model_bw.py
python3 compare/system_model/visualize_makespan.py   --csv compare/results/scar.csv --out compare/results/makespan_scar.png
SCAR_OUT_CSV=compare/results/scar.csv python3 compare/system_model/run_scar_multi_model_bw.py
python3 compare/system_model/visualize_makespan.py   --csv compare/results/scar.csv --out compare/results/makespan_scar.png
python3 compare/system_model/visualize_makespan.py   --csv compare/results/scar.csv --out compare/results/makespan_scar.png
ls
cd 6868
ls
git status
git add -A -- ':!p4.UNI'
ls
cd /home/esp2026/kl3755
git add -A -- ':!p4.UNI'
ls
cd 6868/
ls
git status
cd /home/esp2026/kl3755
git restore --staged . 2>/dev/null
git add -A --   ':!p4.UNI'   ':!.cache' ':!.local' ':!.ssh' ':!.bash_history' ':!.Xauthority'
git status
git commit -m "0413"
git push
cd /path/to/6868
cd 6868
FULLNET_OUT_CSV=compare/results/full_net_bw_layers.csv \
MOBILENET_FULLNET_OUT_CSV=compare/results/mobilenet_full_net_bw_layers.csv   python3 compare/system_model/run_mobilenet_full_network_bw.py
LOOKUP_OUT_CSV=compare/results/layer_accel_lookup_resnet50.csv   python3 compare/system_model/build_layer_lookup.py
python3 compare/system_model/visualize_layer_results.py --kind lookup   --csv compare/results/layer_accel_lookup_resnet50.csv   --out compare/results/plot_layer_lookup.png
ls
cd 686
cd 6868
python3 compare/system_model/visualize_layer_results.py --kind lookup   --csv compare/results/layer_accel_lookup_resnet50.csv   --out compare/results/plot_layer_lookup.png
python3 compare/system_model/visualize_layer_results.py --kind lookup   --csv compare/results/layer_accel_lookup_resnet50.csv   --out compare/results/plot_layer_lookup.png
cd /home/esp2026/kl3755/6868
python3 compare/system_model/visualize_layer_results.py --kind lookup   --csv compare/results/layer_accel_lookup_resnet50.csv   --out compare/results/plot_layer_lookup.png
python3 compare/system_model/visualize_layer_results.py --kind traffic --combo OS_RS   --csv compare/results/full_net_bw_layers.csv   --out compare/results/plot_fullnet_traffic_OS_RS.png
cd /home/esp2026/kl3755/6868
TRAFFIC_PLOT_MAX_XTICKS=66 python3 compare/system_model/visualize_layer_results.py --kind traffic --combo OS_RS   --csv compare/results/full_net_bw_layers.csv   --out compare/results/plot_fullnet_traffic_OS_RS.png
git status
ls
cd 6868
LOOKUP_POLICY=min_makespan SYSTEM_BW=100   LOOKUP_OUT_CSV=compare/results/layer_accel_lookup_resnet50_bw.csv   python3 compare/system_model/build_layer_lookup.py
python3 compare/system_model/visualize_layer_results.py --kind lookup   --csv compare/results/layer_accel_lookup_resnet50_bw.csv   --out compare/results/plot_layer_lookup_bw.png
python3 compare/system_model/visualize_layer_results.py --kind traffic --combo OS_RS   --csv compare/results/full_net_bw_layers.csv   --out compare/results/plot_fullnet_traffic_OS_RS.png
python3 compare/system_model/visualize_layer_results.py --kind lookup   --csv compare/results/layer_accel_lookup_resnet50_bw.csv   --out compare/results/plot_layer_lookup_bw.png
python3 compare/system_model/visualize_layer_results.py --kind lookup   --csv compare/results/layer_accel_lookup_resnet50_bw.csv   --out compare/results/plot_layer_lookup_bw.png
TRAFFIC_PLOT_MAX_XTICKS=66 python3 compare/system_model/visualize_layer_results.py --kind traffic --combo OS_RS   --csv compare/results/full_net_bw_layers.csv   --out compare/results/plot_fullnet_traffic_OS_RS.png
# Change partner
LOOKUP_POLICY=min_makespan SYSTEM_BW=100 LOOKUP_PARTNER_DATAFLOW=NVDLA_WS   LOOKUP_OUT_CSV=compare/results/layer_accel_lookup_resnet50_bw_partnerWS.csv   python3 compare/system_model/build_layer_lookup.py
python3 compare/system_model/visualize_layer_results.py --kind lookup   --csv compare/results/layer_accel_lookup_resnet50_bw_partnerWS.csv   --out compare/results/plot_layer_lookup_bw_partnerWS.png
# Change bandwidth cap
LOOKUP_POLICY=min_makespan SYSTEM_BW=50   LOOKUP_OUT_CSV=compare/results/layer_accel_lookup_resnet50_bw_bw50.csv   python3 compare/system_model/build_layer_lookup.py
python3 compare/system_model/visualize_layer_results.py --kind lookup   --csv compare/results/layer_accel_lookup_resnet50_bw_bw50.csv   --out compare/results/plot_layer_lookup_bw_bw50.png
ls
cd 6868
ls
git status
git push
git commit -m "0423"
git push
SYSTEM_BW=100 GREEDY4_OUT_CSV=compare/results/greedy_four_chiplet_schedule.csv   python3 compare/system_model/run_greedy_four_chiplet.py
python3 compare/system_model/visualize_greedy_four_chiplet.py   --csv compare/results/greedy_four_chiplet_schedule.csv   --out compare/results/greedy_four_chiplet.png
git status
git commit -m "0427"
git push
. "/home/esp2026/kl3755/.cursor-server/bin/linux-x64/e9ee1339915a927dfb2df4a836dd9c8337e17cc0/out/vs/workbench/contrib/terminal/common/scripts/shellIntegration-bash.sh"
. "/home/esp2026/kl3755/.cursor-server/bin/linux-x64/e9ee1339915a927dfb2df4a836dd9c8337e17cc0/out/vs/workbench/contrib/terminal/common/scripts/shellIntegration-bash.sh"
ls
c d6868
cd 6868/
ls
cd p4
python3 compare/system_model/visualize_layer_results.py --kind lookup --drop-last-n 1   --csv compare/results/layer_accel_lookup_resnet50.csv --out compare/results/plot_layer_lookup.png
git status
git commit -m "squeezeNet"
git push
SYSTEM_BW=100 WINDOW_CYCLES=5000000 WINDOW_STRIDE=5000000 MEM_FRAC=0.30   WP4_OUT_CSV=compare/results/windowed_pipelined_four_chiplet_schedule.csv   python3 compare/system_model/run_windowed_pipelined_four_chiplet.py
python3 compare/system_model/visualize_greedy_four_chiplet.py   --csv compare/results/windowed_pipelined_four_chiplet_schedule.csv   --out compare/results/windowed_pipelined_four_chiplet.png
git status
git commit -m "pipelined"
git push
