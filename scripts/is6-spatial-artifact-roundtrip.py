"""Independent process restore of a sealed spatial mesh checkpoint."""
from pathlib import Path
import argparse
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'output/is6-spatial-artifact-staging'))
from is6_spatial_artifact import Store,digest


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--folder',type=Path,required=True);args=parser.parse_args()
    run,view,parent=Store(args.folder).load()
    print(json.dumps(dict(artifact_sha256=digest(run.payload),view=view,lineage_parent=parent,sample=run.sample(view))))


if __name__=='__main__':main()
