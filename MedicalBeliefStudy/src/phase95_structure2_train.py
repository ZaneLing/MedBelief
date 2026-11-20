"""Full-vocabulary small-adapter learning on frozen, teacher-forced states."""
import mlx.optimizers as optim
from mlx.utils import tree_flatten,tree_map
from structure2_core import *

def load_features(folder,depth,cohort):
    xx=[];yy=[];ww=[];ids=[]
    for c in cases():
        if c['cohort']!=cohort:continue
        a=np.load(RUN/'features'/folder/(c['case_id']+'.npz'));xx.append(a[f'x{depth}']);yy.append(a['y']);ww.append(a['weight']);ids += [c['case_id']]*len(a['y'])
    return np.concatenate(xx),np.concatenate(yy),np.concatenate(ww),ids

def source_for(cfg):
    if cfg['name']=='pruned_adapter16':a=read(RUN/'features/pruned_alias.json');return a['folder'],a['depth']
    return 'base',cfg['backbone'].get('exit_layer',28)

def main():
    plan=read(RUN/'adapter_plan.json');model,_=load_model();W=model.model.embed_tokens.weight;mx.eval(W);del model;mx.clear_cache();trained=[]
    for cfg in plan['adapters']:
        dest=RUN/'adapters'/cfg['name'];dest.mkdir(parents=True,exist_ok=True);folder,depth=source_for(cfg)
        if (dest/'completion.json').exists():trained.append(read(dest/'completion.json')['configuration']);continue
        manifest=dict(plan=plan,configuration=cfg,feature_folder=folder,feature_depth=depth,source_sha256=sha(ROOT/'src/phase95_structure2_train.py'),core_sha256=sha(ROOT/'src/structure2_core.py'))
        if (dest/'manifest.json').exists():assert read(dest/'manifest.json')==manifest
        else:write(dest/'manifest.json',manifest)
        x,y,w,trainids=load_features(folder,depth,'train');vx,vy,vw,devids=load_features(folder,depth,'development');assert not set(trainids)&set(devids);assert np.isfinite(x).all() and np.isfinite(vx).all()
        X=mx.array(x);Y=mx.array(y);V=mx.array(vx);VY=mx.array(vy);rng=np.random.default_rng(plan['seed']);mx.random.seed(plan['seed']);adapter=SmallAdapter(cfg['adapter_kind'],cfg['adapter_rank']);adapter.train();optimizer=optim.AdamW(learning_rate=plan['learning_rate'],weight_decay=plan['weight_decay']);mx.eval(adapter.parameters(),X,Y,V,VY)
        def loss(m,a,b):return nn.losses.cross_entropy((m(a)@W.T).astype(mx.float32),b,reduction='mean')
        lossgrad=nn.value_and_grad(adapter,loss)
        def validation():
            total=0.
            for start in range(0,len(vy),32):
                logits=(adapter(V[start:start+32])@W.T).astype(mx.float32);ll=nn.losses.cross_entropy(logits,VY[start:start+32],reduction='none');mx.eval(ll);total+=float(np.sum(np.array(ll)*vw[start:start+32]))
            return total/float(vw.sum())
        history=[];start=time.time();best=validation();best_step=0;adapter.save_weights(str(dest/'best.safetensors'));history.append(dict(step=0,development_loss=best,elapsed=0.));prob=w/w.sum();losses=[]
        for step in range(1,plan['steps']+1):
            ix=mx.array(rng.choice(len(y),size=plan['batch_size'],replace=True,p=prob));ll,grads=lossgrad(adapter,X[ix],Y[ix]);norm=mx.sqrt(sum(mx.sum(g*g) for _,g in tree_flatten(grads)));grads=tree_map(lambda g:g*mx.minimum(1.,1./(norm+1e-8)),grads);optimizer.update(adapter,grads);mx.eval(adapter.parameters(),optimizer.state,ll);value=float(ll.item());assert np.isfinite(value);losses.append(value)
            if step in plan['checkpoints']:
                vl=validation();rr=dict(step=step,development_loss=vl,mean_recent_train_loss=float(np.mean(losses[-100:])),elapsed=round(time.time()-start,2));history.append(rr);print(json.dumps(dict(adapter=cfg['name'],**rr)),flush=True)
                if vl<best:best=vl;best_step=step;adapter.save_weights(str(dest/'best.safetensors'))
                write(dest/'learning_curve.json',history);mx.clear_cache()
        adapter.load_weights(str(dest/'best.safetensors'));np_=sum(v.size for _,v in tree_flatten(adapter.parameters()));new=dict(cfg['backbone'],name=cfg['name'],adapter_file=str((dest/'best.safetensors').relative_to(ROOT)),adapter_kind=cfg['adapter_kind'],adapter_rank=cfg['adapter_rank']);trained.append(new)
        write(dest/'completion.json',dict(complete=True,configuration=new,train_cases=len(set(trainids)),development_cases=len(set(devids)),train_tokens=len(y),development_tokens=len(vy),trainable_parameters=np_,best_step=best_step,best_development_loss=best,initial_development_loss=history[0]['development_loss'],weights_sha256=sha(dest/'best.safetensors'),full_vocabulary_size=W.shape[0],history=history,api_cost_usd=0))
        del adapter,optimizer,X,Y,V,VY;mx.clear_cache()
    write(RUN/'trained_adapters.json',trained);write(RUN/'adapter_training_complete.json',dict(complete=True,configurations=len(trained),api_cost_usd=0))
if __name__=='__main__':main()
