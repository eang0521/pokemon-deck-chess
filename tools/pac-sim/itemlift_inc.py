import json, sys, time
from multiprocessing import Pool
import itemlift2 as L
from items import ITEMS
SH={'DYNAMAX_BAND','SHINY_STONE','EVIOLITE','GOLD_MASK','GOLD_BOTTLE_CAP','ABSORB_BULB','SACRED_ASH','STAR_PIECE','GOLD_BOW','RED_SCALE','RARE_CANDY'}
def keys():
    return [k for k,v in ITEMS.items() if (v['cat'] in ('Component','Crafted','Stone','Tool','Gem') or k in SH) and not any(x in v['flags'] for x in ('slot','econ_income','econ_churn','perm_fire'))]
if __name__=='__main__':
    N=int(sys.argv[1]); out_f=sys.argv[2]; t=time.time()
    ks=keys(); print(len(ks))
    with Pool(2) as p:
        sl=p.map(L.slope_work,[(lv,d,4000,300+lv+d) for lv in L.LEVELS for d in (0,6,12)])
        out=p.map(L.work,[(k,N) for k in ks],chunksize=1)
    json.dump(dict(slope=sl,lift=out,n=N),open(out_f,'w')); print('done',time.time()-t)
