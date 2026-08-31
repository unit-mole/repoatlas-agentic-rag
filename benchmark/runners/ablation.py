VERSIONS=['V0','V1','V2','V3','V4','V5','V6']
def ablation_table(rows):return sorted(rows,key=lambda x:VERSIONS.index(x['version']) if x.get('version') in VERSIONS else 99)
