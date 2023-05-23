import json, yaml
import os
import h5py as h5
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import gridspec
import matplotlib.ticker as mtick
from sklearn.utils import shuffle
import tensorflow as tf
from keras.utils.np_utils import to_categorical
import energyflow as ef

np.random.seed(0) #fix the seed to keep track of validation split

line_style = {
    'true':'dotted',
    'gen':'-',
    'Geant':'dotted',
    'GSGM':'-',
    'q_truth':'-',
    'q_gen':'dotted',
    'g_truth':'-',
    'g_gen':'dotted',
    't_truth':'-',
    't_gen':'dotted',
    'w_truth':'-',
    'w_gen':'dotted',
    'z_truth':'-',
    'z_gen':'dotted',

    't_gen_d64':'dotted',
    't_gen_d256':'dotted',
    
}

colors = {
    'true':'black',
    'gen':'#7570b3',
    'Geant':'black',
    'GSGM':'#7570b3',

    'q_truth':'#7570b3',
    'q_gen':'#7570b3',
    'g_truth':'#d95f02',
    'g_gen':'#d95f02',
    't_truth':'#1b9e77',
    't_gen':'#1b9e77',
    'w_truth':'#e7298a',
    'w_gen':'#e7298a',
    'z_truth':'black',
    'z_gen':'black',

    't_gen_d64':'red',
    't_gen_d256':'blue',

}

name_translate={
    'true':'True distribution',
    'gen':'Generated distribution',
    'Geant':'Geant 4',
    'GSGM':'Graph Diffusion',

    'q_truth':'Sim.: q',
    'q_gen':'FPCD: q',
    'g_truth':'Sim.: g',
    'g_gen':'FPCD: g',
    't_truth':'Sim.: top',
    't_gen':'FPCD: top',
    'w_truth':'Sim.: W',
    'w_gen':'FPCD: W',
    'z_truth':'Sim.: Z',
    'z_gen':'FPCD: Z',

    't_gen_d64':'FPCD: top 8 steps',
    't_gen_d256':'FPCD: top 2 steps',
    }

names = ['g','q','t','w','z']

labels200 = {
    # 'truncated_200cells_FPCD.hdf5':0,
    'improved_200cells_FPCD.hdf5':0,
    }

labels1000 = {
    'truncated_1000cells_FPCD.hdf5':0,
}

# nevts = -1
nevts = 100_000
num_classes = 5
num_classes_eval = 5


def SetStyle():
    from matplotlib import rc
    rc('text', usetex=True)

    import matplotlib as mpl
    rc('font', family='serif')
    rc('font', size=22)
    rc('xtick', labelsize=15)
    rc('ytick', labelsize=15)
    rc('legend', fontsize=15)

    # #
    mpl.rcParams.update({'font.size': 19})
    #mpl.rcParams.update({'legend.fontsize': 18})
    mpl.rcParams['text.usetex'] = False
    mpl.rcParams.update({'xtick.labelsize': 18}) 
    mpl.rcParams.update({'ytick.labelsize': 18}) 
    mpl.rcParams.update({'axes.labelsize': 18}) 
    mpl.rcParams.update({'legend.frameon': False}) 
    mpl.rcParams.update({'lines.linewidth': 2})
    
    import matplotlib.pyplot as plt
    import mplhep as hep
    # hep.set_style(hep.style.CMS)
    # mplhep.style.use(hep.style.CMS)
    hep.style.use("CMS") 

def SetGrid(ratio=True):
    fig = plt.figure(figsize=(9, 9))
    if ratio:
        gs = gridspec.GridSpec(2, 1, height_ratios=[3,1]) 
        gs.update(wspace=0.025, hspace=0.1)
    else:
        gs = gridspec.GridSpec(1, 1)
    return fig,gs



        
def PlotRoutine(feed_dict,xlabel='',ylabel='',reference_name='gen'):
    assert reference_name in feed_dict.keys(), "ERROR: Don't know the reference distribution"
    
    fig,gs = SetGrid() 
    ax0 = plt.subplot(gs[0])
    plt.xticks(fontsize=0)
    ax1 = plt.subplot(gs[1],sharex=ax0)

    for ip,plot in enumerate(feed_dict.keys()):
        if 'steps' in plot or 'r=' in plot:
            ax0.plot(np.mean(feed_dict[plot],0),label=plot,marker=line_style[plot],color=colors[plot],lw=0)
        else:
            ax0.plot(np.mean(feed_dict[plot],0),label=plot,linestyle=line_style[plot],color=colors[plot])
        if reference_name!=plot:
            ratio = 100*np.divide(np.mean(feed_dict[reference_name],0)-np.mean(feed_dict[plot],0),np.mean(feed_dict[reference_name],0))
            #ax1.plot(ratio,color=colors[plot],marker='o',ms=10,lw=0,markerfacecolor='none',markeredgewidth=3)
            if 'steps' in plot or 'r=' in plot:
                ax1.plot(ratio,color=colors[plot],markeredgewidth=1,marker=line_style[plot],lw=0)
            else:
                ax1.plot(ratio,color=colors[plot],linewidth=2,linestyle=line_style[plot])
                
        
    FormatFig(xlabel = "", ylabel = ylabel,ax0=ax0)
    ax0.legend(loc='best',fontsize=16,ncol=1)

    plt.ylabel('Difference. (%)')
    plt.xlabel(xlabel)
    plt.axhline(y=0.0, color='r', linestyle='--',linewidth=1)
    plt.axhline(y=10, color='r', linestyle='--',linewidth=1)
    plt.axhline(y=-10, color='r', linestyle='--',linewidth=1)
    plt.ylim([-100,100])

    return fig,ax0

class ScalarFormatterClass(mtick.ScalarFormatter):
    #https://www.tutorialspoint.com/show-decimal-places-and-scientific-notation-on-the-axis-of-a-matplotlib-plot
    def _set_format(self):
        self.format = "%1.1f"


def FormatFig(xlabel,ylabel,ax0):
    #Limit number of digits in ticks
    # y_loc, _ = plt.yticks()
    # y_update = ['%.1f' % y for y in y_loc]
    # plt.yticks(y_loc, y_update) 
    ax0.set_xlabel(xlabel,fontsize=20)
    ax0.set_ylabel(ylabel)
        

    # xposition = 0.9
    # yposition=1.03
    # text = 'H1'
    # WriteText(xposition,yposition,text,ax0)


def WriteText(xpos,ypos,text,ax0):

    plt.text(xpos, ypos,text,
             horizontalalignment='center',
             verticalalignment='center',
             transform = ax0.transAxes, fontsize=25, fontweight='bold')


def HistRoutine(feed_dict,
                xlabel='',ylabel='',
                reference_name='Geant',
                logy=False,binning=None,
                fig = None, gs = None,
                plot_ratio= True,
                idx = None,
                label_loc='best'):
    assert reference_name in feed_dict.keys(), "ERROR: Don't know the reference distribution"

    if fig is None:
        fig,gs = SetGrid(plot_ratio) 
    ax0 = plt.subplot(gs[0])
    if plot_ratio:
        plt.xticks(fontsize=0)
        ax1 = plt.subplot(gs[1],sharex=ax0)
        
    
    if binning is None:
        binning = np.linspace(np.quantile(feed_dict[reference_name],0.0),np.quantile(feed_dict[reference_name],1),20)
        
    xaxis = [(binning[i] + binning[i+1])/2.0 for i in range(len(binning)-1)]
    reference_hist,_ = np.histogram(feed_dict[reference_name],bins=binning,density=True)
    maxy = np.max(reference_hist)
    
    for ip,plot in enumerate(feed_dict.keys()):
        dist,_,_=ax0.hist(feed_dict[plot],bins=binning,label=name_translate[plot],linestyle=line_style[plot],color=colors[plot],density=True,histtype="step")
        if plot_ratio:
            if reference_name!=plot:
                ratio = 100*np.divide(reference_hist-dist,reference_hist)
                ax1.plot(xaxis,ratio,color=colors[plot],marker='o',ms=10,lw=0,markerfacecolor='none',markeredgewidth=3)
        
    ax0.legend(loc=label_loc,fontsize=12,ncol=5)

    if logy:
        ax0.set_yscale('log')



    if plot_ratio:
        FormatFig(xlabel = "", ylabel = ylabel,ax0=ax0)
        plt.ylabel('Difference. (%)')
        plt.xlabel(xlabel)
        plt.axhline(y=0.0, color='r', linestyle='-',linewidth=1)
        # plt.axhline(y=10, color='r', linestyle='--',linewidth=1)
        # plt.axhline(y=-10, color='r', linestyle='--',linewidth=1)
        plt.ylim([-100,100])
    else:
        FormatFig(xlabel = xlabel, ylabel = ylabel,ax0=ax0)
    
    return fig,gs, binning


def LoadJson(file_name):
    import json,yaml
    JSONPATH = os.path.join(file_name)
    return yaml.safe_load(open(JSONPATH))

def SaveJson(save_file,data):
    with open(save_file,'w') as f:
        json.dump(data, f)


def revert_npart(npart,max_npart):

    #Revert the preprocessing to recover the cell multiplicity
    alpha = 1e-6
    data_dict = LoadJson('preprocessing_{}.json'.format(max_npart))
    x = npart*data_dict['std_cluster'][-1] + data_dict['mean_cluster'][-1]
    x = revert_logit(x)
    x = x * (data_dict['max_cluster'][-1]-data_dict['min_cluster'][-1]) + data_dict['min_cluster'][-1]
    #x = np.exp(x)
    return np.round(x).astype(np.int32)
     
def revert_logit(x):
    alpha = 1e-6
    exp = np.exp(x)
    x = exp/(1+exp)
    return (x-alpha)/(1 - 2*alpha)                

def ReversePrep(cells,clusters,npart):

    alpha = 1e-6
    data_dict = LoadJson('preprocessing_{}.json'.format(npart))
    num_part = cells.shape[1]    
    cells=cells.reshape(-1,cells.shape[-1])
    print(f"\nCells shape = {np.shape(cells)}\n")
    
    mask=np.expand_dims(cells[:,2]!=0,-1)#"Mask" data removed, just checks if feature 2 !=0
    def _revert(x,name='cluster'):    
        x = x*data_dict['std_{}'.format(name)] + data_dict['mean_{}'.format(name)]
        x = revert_logit(x)
        #print(data_dict['max_{}'.format(name)],data_dict['min_{}'.format(name)])
        x = x * (np.array(data_dict['max_{}'.format(name)]) -data_dict['min_{}'.format(name)]) + data_dict['min_{}'.format(name)]
        return x
        
    cells = _revert(cells,'cell')
    clusters = _revert(clusters,'cluster')
    clusters[:,-1] = np.round(clusters[:,-1]) #num cells
    return (cells*mask).reshape(clusters.shape[0],num_part,-1),clusters


def SimpleLoader(data_path,labels):
    #FIXME: Simple Loader needs to split cluster into cluster+cond.!!!!
    cells = []
    clusters = []

    for label in labels:
        #if 'w' in label or 'z' in label: continue #no evaluation for w and z
        with h5.File(os.path.join(data_path,label),"r") as h5f:
            ntotal = h5f['cluster'][:].shape[0]
            cell = h5f['hcal_cells'][int(0.7*ntotal):].astype(np.float32)
            cluster = h5f['cluster'][int(0.7*ntotal):].astype(np.float32)
            cluster = np.concatenate([cluster,labels[label]*np.ones(shape=(cluster.shape[0],1),dtype=np.float32)],-1)

            cells.append(cell)
            clusters.append(cluster)

    cells = np.concatenate(cells)
    clusters = np.concatenate(clusters)
    cells,clusters = shuffle(cells,clusters, random_state=0)


    # mask = np.sqrt(cells[:,:,0]**2 + cells[:,:,1]**2) < 0.8 #eta looks off
    # cells*=np.expand_dims(mask,-1)

    # cond = to_categorical(clusters[:nevts,-1], num_classes=num_classes)
    mask = np.expand_dims(cells[:nevts,:,-1],-1)

    return cells[:nevts,:,:-1]*mask,clusters[:nevts],cond


def DataLoader(data_path,labels,
               npart,
               rank=0,size=1,
               num_condition=2,#genP,genTheta
               batch_size=64,make_tf_data=True):
    cells = []
    clusters = []

    def _preprocessing(cells,clusters,save_json=False):
        num_part = cells.shape[1]
        #eta cut removed here
        # mask = np.expand_dims(cells[:,:,-1],-1)
        # cells = cells[:,:,:-1]*mask
        print(f"\n\nSHAPE OF CELLS in _preprocess = {np.shape(cells)}")
        cells=cells.reshape(-1,cells.shape[-1]) #flatten
        print(f"\n\nSHAPE OF CELLS in _preprocess = {np.shape(cells)}")

        def _logit(x):                            
            alpha = 1e-6
            x = alpha + (1 - 2*alpha)*x
            return np.ma.log(x/(1-x)).filled(0)

        #Transformations

        if save_json:
            mask = cells[:,-1] == 1 #saves array of BOOLS instead of ints
            print(f"SHAPE OF MASK in _preprocess = {np.shape(mask)}")
            print(f"SHAPE OF MASKED in _preprocess = {np.shape(cells[mask])}")
            # print(f"SHAPE OF MASKED* in _preprocess = {np.shape(cells*mask)}")
            
            data_dict = {
                'max_cluster':np.max(clusters[:,:],0).tolist(),
                'min_cluster':np.min(clusters[:,:],0).tolist(),
                'max_cell':np.max(cells[mask][:,:-1],0).tolist(), #-1 avoids mask
                'min_cell':np.min(cells[mask][:,:-1],0).tolist(),
            }                
            
            SaveJson('preprocessing_{}.json'.format(npart),data_dict)
        else:
            data_dict = LoadJson('preprocessing_{}.json'.format(npart))


        # print(f"\nL 359: Clusters in DataLoader Before Norm= {clusters[0]}\n")

        #normalize
        clusters[:,:] = np.ma.divide(clusters[:,:]-data_dict['min_cluster'],np.array(data_dict['max_cluster'])- data_dict['min_cluster']).filled(0)        
        cells[:,:-1]= np.ma.divide(cells[:,:-1]-data_dict['min_cell'],np.array(data_dict['max_cell'])- data_dict['min_cell']).filled(0)

        # make gaus-like. 
        clusters = _logit(clusters)
        cells[:,:-1] = _logit(cells[:,:-1])

        if save_json:
            mask = cells[:,-1]
            mean_cell = np.average(cells[:,:-1],axis=0,weights=mask)
            data_dict['mean_cluster']=np.mean(clusters,0).tolist()
            data_dict['std_cluster']=np.std(clusters,0).tolist()
            data_dict['mean_cell']=mean_cell.tolist()
            data_dict['std_cell']=np.sqrt(np.average((cells[:,:-1] - mean_cell)**2,axis=0,weights=mask)).tolist()                        
            SaveJson('preprocessing_{}.json'.format(npart),data_dict)


        clusters = np.ma.divide(clusters-data_dict['mean_cluster'],data_dict['std_cluster']).filled(0)
        cells[:,:-1]= np.ma.divide(cells[:,:-1]-data_dict['mean_cell'],data_dict['std_cell']).filled(0)

        cells = cells.reshape(clusters.shape[0],num_part,-1)
        # print(f"\nL 380: Shape of Cells in DataLoader = {np.shape(cells)}\n")
        # print(f"\nL 381: Cells in DataLoader = {cells[0,:,:-1]}\n")
        # print(f"\nL 382: Clusters in DataLoader = {clusters}\n")
        return cells.astype(np.float32),clusters.astype(np.float32)


    for label in labels:

        with h5.File(os.path.join(data_path,label),"r") as h5f:
            ntotal = h5f['cluster'][:].shape[0]
            # ntotal = nevts

            if make_tf_data:
                cell = h5f['hcal_cells'][rank:int(0.7*ntotal):size].astype(np.float32)
                cluster = h5f['cluster'][rank:int(0.7*ntotal):size].astype(np.float32)
                # print(f"cluster from H5 file = {cluster[0]}")
                # cluster = np.concatenate([cluster,labels[label]*np.ones(shape=(cluster.shape[0],1),dtype=np.float32)],-1)

            else:
                #load evaluation data
                #if 'w' in label or 'z' in label: continue #no evaluation for w and z
                cell = h5f['hcal_cells'][int(0.7*ntotal):].astype(np.float32)
                cluster = h5f['cluster'][int(0.7*ntotal):].astype(np.float32)
                # cluster = np.concatenate([cluster,labels[label]*np.ones(shape=(cluster.shape[0],1),dtype=np.float32)],-1)           


            cells.append(cell)
            clusters.append(cluster)

    cells = np.concatenate(cells)
    clusters = np.concatenate(clusters)
    # cond = clusters[:,:2]#GenP, GenTheta
    cond = clusters[:,:num_condition]#GenP, GenTheta 
    cond[:,0] = np.log10(cond[:,0]) #Log10 of GenP
    clusters = clusters[:,2:] #ClusterSum, N_Hits

    # print(f"L407:\n JET SHAPE = {np.shape(clusters)}\n")
    # print(f"cell SHAPE = {np.shape(cells)}\n")
    cells,clusters,cond = shuffle(cells,clusters,cond, random_state=0)

    data_size = clusters.shape[0]
    # mask = np.expand_dims(cells[:nevts,:,-1],-1)
    cells,clusters = _preprocessing(cells,clusters,save_json=True) #set to false after 1st
    # cells,clusters = _preprocessing(cells,clusters,save_json=False)    
    

    if make_tf_data:
        train_cells = cells[:int(0.8*data_size)] #This is 80% train (whcih 70% of total)
        train_clusters = clusters[:int(0.8*data_size)]
        train_cond = cond[:int(0.8*data_size)]
        
        test_cells = cells[int(0.8*data_size):]
        test_clusters = clusters[int(0.8*data_size):]
        test_cond = cond[int(0.8*data_size):]
        
    
        def _prepare_batches(cells,clusters,cond):
            
            nevts = clusters.shape[0]
            tf_cluster = tf.data.Dataset.from_tensor_slices(clusters)

            # cond = to_categorical(clusters[:,-1], num_classes=num_classes) 
            # cond = np.ones(np.shape(clusters)[0])

            tf_cond = tf.data.Dataset.from_tensor_slices(cond)
            mask = np.expand_dims(cells[:,:,-1],-1)
            masked = cells[:,:,:-1]*mask
            # print("\n\nMasked cells = \n\n",masked)
            tf_part = tf.data.Dataset.from_tensor_slices(masked)
            tf_mask = tf.data.Dataset.from_tensor_slices(mask)
            tf_zip = tf.data.Dataset.zip((tf_part, tf_cluster,tf_cond,tf_mask))
            return tf_zip.shuffle(nevts).repeat().batch(batch_size)
    
        train_data = _prepare_batches(train_cells,train_clusters,train_cond)
        test_data  = _prepare_batches(test_cells,test_clusters,test_cond)    
        return data_size, train_data,test_data
    
    else:
        #FIXME: Need to change the condition from jet type to genP
        # cond = clusters[:,0] # Generated Momentum
        # cond = to_categorical(clusters[:nevts,-1], num_classes=num_classes_eval)

        # cond = np.concatenate([cond,np.zeros(shape=(cond.shape[0],num_classes-num_classes_eval), dtype=np.float32)], -1)

        mask = np.expand_dims(cells[:nevts,:,-1],-1)
        # print("\n\nMask applide to Cells = \n\n",cells[0,:,:,-1]*mask[0])
        return cells[:nevts,:,:-1]*mask,clusters[:nevts], cond[:nevts]
