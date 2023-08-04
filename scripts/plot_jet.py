import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from matplotlib import gridspec
import argparse
import h5py as h5
import os
import utils
import tensorflow as tf
from GSGM import GSGM
from GSGM_distill import GSGM_distill
import time
import gc
import sys
sys.path.append("JetNet")
from jetnet.evaluation import w1p,w1m,w1efp,cov_mmd,fpnd
from scipy.stats import wasserstein_distance
from plot_class import PlottingConfig

def W1(
        cluster1,
        cluster2,
        num_batches = 10,
        return_std = True,
        num_eval=50000,
):

    w1s = []
    
    for j in range(num_batches):
        rand1 = np.random.choice(len(cluster1), size=num_eval,replace=True)
        rand2 = np.random.choice(len(cluster2), size=num_eval,replace=True)

        rand_sample1 = cluster1[rand1]
        rand_sample2 = cluster2[rand2]

        w1 = [wasserstein_distance(rand_sample1, rand_sample2)]
        w1s.append(w1)
        
    means = np.mean(w1s, axis=0)
    stds = np.std(w1s, axis=0)
    return means, stds

def plot(cluster1,cluster2,cond1,cond2,nplots,title,plot_folder,is_big):
    for ivar in range(nplots):
        config = PlottingConfig(title,ivar,is_big)

        name = utils.names[ivar]
        feed_dict = {
            '{}_truth'.format(name):cluster1[:,ivar],
            '{}_gen'.format(name):  cluster2[:,ivar]
        }

        if i == 0:                            
            fig,gs,_ = utils.HistRoutine(feed_dict,xlabel=config.var,
                                         binning=config.binning,
                                         plot_ratio=False,
                                         reference_name='{}_truth'.format(name),
                                         ylabel= 'Normalized entries',logy=config.logy)
        else:
            fig,gs,_ = utils.HistRoutine(feed_dict,xlabel=config.var,
                                         reference_name='{}_truth'.format(name),
                                         plot_ratio=False,
                                         fig=fig,gs=gs,binning=config.binning,
                                         ylabel= 'Normalized entries',logy=config.logy)
        ax0 = plt.subplot(gs[0])     
        ax0.set_ylim(top=config.max_y)
        if config.logy == False:
            yScalarFormatter = utils.ScalarFormatterClass(useMathText=True)
            yScalarFormatter.set_powerlimits((100,0))
            ax0.yaxis.set_major_formatter(yScalarFormatter)

        if not os.path.exists(plot_folder):
            os.makedirs(plot_folder)
        fig.savefig('{}/GSGM_{}_{}.pdf'.format(plot_folder,title,ivar),bbox_inches='tight')


if __name__ == "__main__":
    print( "Running plot_jet.py as script" )
    gpus = tf.config.experimental.list_physical_devices('GPU')
    for gpu in gpus:
        tf.config.experimental.set_memory_growth(gpu, True)


    utils.SetStyle()


    parser = argparse.ArgumentParser()

    parser.add_argument('--data_folder', default='./', help='Folder containing data and MC files')
    parser.add_argument('--plot_folder', default='../plots', help='Folder to save results')
    parser.add_argument('--config', default='config_cluster.json', help='Training parameters')

    parser.add_argument('--model', default='GSGM', help='Type of generative model to load')
    parser.add_argument('--distill', action='store_true', default=False,help='Use the distillation model')
    parser.add_argument('--test', action='store_true', default=False,help='Test if inverse transform returns original data')
    parser.add_argument('--big', action='store_true', default=False,help='Use bigger dataset (1000 cells) as opposed to 200 cells')
    parser.add_argument('--sample', action='store_true', default=False,help='Sample from the generative model')
    parser.add_argument('--comp', action='store_true', default=False, help='Compare the results for diffusion models with different diffusion steps')
    parser.add_argument('--factor', type=int,default=1, help='Step reduction for distillation model')


    flags = parser.parse_args()
    config = utils.LoadJson(flags.config)

    if flags.big:
        labels = utils.labels1000
        npart=1000
    else:
        labels=utils.labels200
        npart=200

    cells, clusters, condition = utils.DataLoader(flags.data_folder,
                                                  labels=labels,
                                                  npart=npart,
                                                  num_condition=config['NUM_COND'],
                                                  make_tf_data=False)

    if flags.test:
        cells_gen, clusters_gen, condition_gen = utils.SimpleLoader(flags.data_folder,labels=labels)
        sample_name = "test_mode"

    else:
        model_name = config['MODEL_NAME']
        if flags.big:
            model_name+='_big'

        sample_name = model_name
        if flags.distill:
            sample_name += '_d{}'.format(flags.factor)



        if flags.sample:            
            model = GSGM(config=config,factor=flags.factor,npart=npart)
            checkpoint_folder = '../checkpoints_{}/checkpoint'.format(model_name)
            # checkpoint_folder = '../checkpoints_GSGM_128mlp/checkpoint'.format(model_name)
            if flags.distill:
                checkpoint_folder = '../checkpoints_{}_d{}/checkpoint'.format(model_name,flags.factor)
                model = GSGM_distill(model.ema_cluster,model.ema_part,config=config,
                                     factor=flags.factor,npart=npart)
                print("Loading distilled model from: {}".format(checkpoint_folder))
            model.load_weights('{}'.format(checkpoint_folder)).expect_partial()

            cells_gen = []
            clusters_gen = []

            # nsplit = 100 #number of batches, in which to split nevts in utils.py
            nsplit = 4 #number of batches, in which to split nevts in utils.py

            split_part = np.array_split(clusters,nsplit)
            for i,split in enumerate(np.array_split(condition,nsplit)):
                #,split_part[i]
                # genP as input to model.genearet()
                start = time.time()
                p,j = model.generate(split,split_part[i])
                print(f"Time to sample {np.shape(split_part[i])[0]} events is {time.time() - start} seconds")
                cells_gen.append(p)
                clusters_gen.append(j)

            cells_gen = np.concatenate(cells_gen)
            clusters_gen = np.concatenate(clusters_gen)

            print("L 162: ReversePrep Call")
            cells_gen, clusters_gen = utils.ReversePrep(cells_gen,clusters_gen,npart=npart)
            # clusters_gen = np.concatenate([clusters_gen,np.expand_dims(np.argmax(condition,-1),-1)],-1)

            with h5.File(os.path.join(flags.data_folder,sample_name+'.h5'),"w") as h5f:
                dset = h5f.create_dataset("cell_features", data=cells_gen)
                dset = h5f.create_dataset("cluster_features", data=clusters_gen)

        else:
            with h5.File(os.path.join(flags.data_folder,sample_name+'.h5'),"r") as h5f:
                cells_gen = h5f['cell_features'][:]
                clusters_gen = h5f['cluster_features'][:]

        condition_gen = clusters_gen[:,-1]

        # assert np.all(condition_gen == np.argmax(condition,-1)), 'The order between the cells dont match'
        clusters_gen = clusters_gen[:,:-1]

    print("L 179: ReversePrep Call")
    cells, clusters = utils.ReversePrep(cells,clusters,npart=npart)

    plot(clusters,clusters_gen,condition,condition,title='cluster',
         nplots=2,plot_folder=flags.plot_folder,is_big=flags.big)

    # print("Calculating metrics")

    #with open(sample_name+'.txt','w') as f:
    #    # for unique in np.unique(np.argmax(condition,-1)):
    #    for icond in condition:
    #        p_gen = icond[0]  #P_Gen. 1=> Theta_Gen
    #        mask = np.argmax(condition,-1)== p_gen
    #        print(utils.names[p_gen])
    #        f.write(utils.names[p_gen])
    #        f.write("\n")
    #        mean_mass,std_mass = w1m(cells[mask], cells_gen[mask])
    #        print("W1M",mean_mass,std_mass)
    #        f.write("{:.2f} $\pm$ {:.2f} & ".format(1e3*mean_mass,1e3*std_mass))            
    #        mean,std = w1p(cells[mask], cells_gen[mask])
    #        print("W1P: ",np.mean(mean),mean,np.mean(std))
    #        f.write("{:.2f} $\pm$ {:.2f} & ".format(1e3*np.mean(mean),1e3*np.mean(std)))
    #        mean_efp,std_efp = w1efp(cells[mask], cells_gen[mask])
    #        print("W1EFP",np.mean(mean_efp),np.mean(std_efp))
    #        f.write("{:.2f} $\pm$ {:.2f} & ".format(1e5*np.mean(mean_efp),1e5*np.mean(std_efp)))
    #        if flags.big or 'w' in utils.names[p_gen] or 'z' in utils.names[p_gen]:
    #            #FPND only defined for 30 cells and not calculated for W and Z
    #            pass
    #        else:
    #            fpnd_score = fpnd(cells_gen[mask], cluster_type=utils.names[p_gen])
    #            print("FPND", fpnd_score)
    #            f.write("{:.2f} & ".format(fpnd_score))

    #        cov,mmd = cov_mmd(cells[mask],cells_gen[mask],num_eval_samples=1000)
    #        print("COV,MMD",cov,mmd)
    #        f.write("{:.2f} & {:.2f} \\\\".format(cov,mmd))
    #        f.write("\n")


    #    for unique in np.unique(np.argmax(condition,-1)):
    #        mask = np.argmax(condition,-1)== unique

    #        print("Jet "+utils.names[unique])
    #        f.write("Jet "+utils.names[unique])
    #        f.write("\n")
    #        for i in range(clusters_gen.shape[-1]):
    #            mean,std=W1(clusters_gen[:,i],clusters[:,i])
    #            print("W1J {:.2f}: {:.2f}".format(i,mean[0],std[0]))
    #            f.write("{:.3f} $\pm$ {:.3f}&".format(np.mean(mean),np.mean(std)))
    #         f.write("\\ \n")

    condition = np.tile(np.expand_dims(condition,1),(1,cells_gen.shape[1],1)).reshape((-1,condition.shape[-1]))

    cells_gen=cells_gen.reshape((-1,3))
    mask_gen = cells_gen[:,2]>0.
    cells_gen=cells_gen[mask_gen]
    cells=cells.reshape((-1,3))
    mask = cells[:,2]>0.
    cells=cells[mask]

    condition_gen = condition[mask_gen]
    condition = condition[mask]


    plot(cells,cells_gen,
         condition,condition_gen,
         title='part',
         nplots=4,
         plot_folder=flags.plot_folder,
         is_big=flags.big)


