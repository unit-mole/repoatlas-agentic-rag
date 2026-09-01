from pathlib import Path
import gradio as gr
from repoatlas.pipeline import build_runtime
RUNTIME=None

def load_repo(path):
    global RUNTIME
    p=Path(path)
    if not p.exists():return 'Repository path not found.'
    RUNTIME=build_runtime(p,embedding='hash',reranker='heuristic')
    return f"Indexed {len(RUNTIME['symbols'])} symbols; graph {RUNTIME['graph'].number_of_nodes()} nodes / {RUNTIME['graph'].number_of_edges()} edges."
def investigate(task,hops):
    if RUNTIME is None:return {'error':'Index a repository first.'}
    return RUNTIME['engine'].investigate(task,int(hops))
with gr.Blocks(title='RepoAtlas') as demo:
    gr.Markdown('# RepoAtlas\nGraph-enhanced repository intelligence. Public-safe/read-only defaults.')
    with gr.Row():
        repo=gr.Textbox(value='data/fixture_repo',label='Repository path'); load=gr.Button('Index repository')
    status=gr.Textbox(label='Index status'); load.click(load_repo,repo,status)
    task=gr.Textbox(lines=5,label='Task',value='Investigate which symbols are affected if cache timeout behavior changes and identify related tests.')
    hops=gr.Slider(0,2,value=2,step=1,label='Graph hops'); run=gr.Button('Investigate'); result=gr.JSON(label='Investigation report');run.click(investigate,[task,hops],result)
if __name__=='__main__': demo.launch()
