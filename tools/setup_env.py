"""Install a fresh environment; never copy an environment from another machine."""
import argparse,platform,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('backend',choices=['analysis','mlx']);ap.add_argument('--python',default=sys.executable);a=ap.parse_args()
 if a.backend=='mlx' and (platform.system()!='Darwin' or platform.machine()!='arm64'):raise SystemExit("MLX requires native Apple Silicon macOS. This snapshot's experimental backend is MLX on Apple Silicon.")
 name={'analysis':'.runtime','mlx':'.runtime_mlx'}[a.backend];env=ROOT/'MedicalBeliefMechanisms'/name
 if not env.exists():subprocess.run([a.python,'-m','venv',str(env)],check=True)
 py=env/('Scripts/python.exe' if platform.system()=='Windows' else 'bin/python')
 subprocess.run([str(py),'-m','pip','install','--upgrade','pip'],check=True)
 req=a.backend
 subprocess.run([str(py),'-m','pip','install','-r',str(ROOT/'requirements'/(req+'.txt'))],check=True)
 print('Environment ready:',py)
if __name__=='__main__':main()
