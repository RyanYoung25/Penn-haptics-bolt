#! /usr/bin/python
import cPickle
import os
import sys
import itertools
import utilities
from utilities import adjectives, phases, sensors, static_features
import multiprocessing
import tables
import traceback
import numpy as np
from static_feature_obj import StaticFeatureObj
import upenn_features
from collections import defaultdict
import sklearn
from sklearn.externals.joblib import Parallel, delayed
from sklearn.metrics import f1_score
from sklearn.pipeline import Pipeline
from safe_leave_p_out import SafeLeavePLabelOut

def load_adjective_phase(base_directory):

    adjective_dir = os.path.join(base_directory, "adjective_phase_set")
    all_features = defaultdict(dict)

    for f in os.listdir(adjective_dir):
        # select pkl files associated with adjective
        if not f.endswith('.pkl'):
            continue
        
        # Load pickle file
        path_name = os.path.join(adjective_dir, f)
        with open(path_name, "r") as file_path:
            features = cPickle.load(file_path)

        chars = f.strip(".pkl").split("_")
        chars = chars[2:] #static_feature
        adjective = chars[0] #adjective
        chars = chars[1:] #adjective
        phase = "_".join(chars) # merge together
        all_features[adjective][phase] = features

    return all_features

def original_train_adjective_phase_classifier(path, adjective, phase, all_features, boost):
    """
    Example function on how to access all of the features
    stored in adjective_phase_set
    """

    # File name 
    dataset_file_name = "_".join(("trained", adjective, phase))+".pkl"
    newpath = os.path.join(path, "trained_adjective_phase")
    path_name = os.path.join(newpath, dataset_file_name)
    
    if os.path.exists(path_name):
        print "File %s already exists, skipping it." % path_name
        return

    print "Creating adjective %s and phase %s" % (adjective, phase)

    train_set = all_features[adjective][phase]['train']
    train_X = train_set['features']
    train_Y = train_set['labels']
    object_ids = train_set['object_ids']
    

    print "Training adjective %s and phase %s" %(adjective, phase)

    #magic training happening here!!!
    leav_out = 3 
    clf = Pipeline([
        ('scaler', sklearn.preprocessing.StandardScaler()),
        ('svm', sklearn.svm.LinearSVC()), 
         ])   
    
    #cv = sklearn.cross_validation.LeavePLabelOut(train_ids, leav_out)
    cv = SafeLeavePLabelOut(object_ids, leav_out, 100, train_Y)
    parameters = { 
        #'svm_C': np.linspace(0.001,1e6,100),
        #'svm__C': [10101.011090909091 ],
        'svm__C': np.linspace(1e2, 1e6, 100),    
        #'svm__penalty': ['l2','l1'],
        'svm__penalty': ['l2'],
        'svm__dual': [False],
        'svm__class_weight' : ('auto',),
                  }

    verbose = 1
    grid = sklearn.grid_search.GridSearchCV(clf, parameters,
                                            n_jobs=1,
                                            cv=cv,
                                            score_func=f1_score,
                                            verbose=verbose)
    grid.fit(train_X, train_Y)
    trained_clf = grid.best_estimator_
 
    '''
    if not boost:
        trained_clf, scaler = utilities.train_svm_gridsearch(train_X = train_X,
                             train_Y = train_Y,
                             verbose=True,
                             #object_ids = object_ids,
                             n_jobs = 6,
                             scale = True 
                             )   
    else: 
        trained_clf, scaler = utilities.train_gradient_boost(train_X = train_X,
                                train_Y = train_Y,
                                object_ids = object_ids,
                                verbose = True, 
                                n_jobs = 6,
                                scale = True
                                )

    '''
    dataset = all_features[adjective][phase]
    dataset['adjective'] = adjective
    dataset['phase'] = phase
    dataset['classifier'] = trained_clf
    #dataset['scaler'] = scaler
   
    print "Saving trained_classifier" 

    # Save the results in the folder
    with open(path_name, "w") as f:
        print "Saving file: ", path_name
        cPickle.dump(dataset, f, protocol=cPickle.HIGHEST_PROTOCOL)

def alt_train_adjective_phase_classifier(path, adjective, phase, all_features):
    """
    Example function on how to access all of the features
    stored in adjective_phase_set
    """

    # File name 
    dataset_file_name = "_".join(("trained", adjective, phase))+".pkl"
    newpath = os.path.join(path, "trained_adjective_phase")
    path_name = os.path.join(newpath, dataset_file_name)
    
    if os.path.exists(path_name):
        print "File %s already exists, skipping it." % path_name
        return

    #print "Creating adjective %s and phase %s" % (adjective, phase)

    train_set = all_features[adjective][phase]['train']
    train_X = train_set['features']
    train_Y = train_set['labels']
    object_ids = train_set['object_ids']

    print "Training adjective %s and phase %s" %(adjective, phase)
    
    
    #magic training happening here!!!
    scaler = sklearn.preprocessing.StandardScaler().fit(train_X)
    train_X = scaler.transform(train_X)    
    parameters = {'C': np.linspace(0.001,1e6,100),              
                  'penalty': ['l2','l1'],
                  'dual': [False],
                  'class_weight' : ('auto',),
                  }
    clf = sklearn.svm.LinearSVC()
    grid = sklearn.grid_search.GridSearchCV(clf, parameters,
                                            n_jobs=1,
                                            score_func=f1_score)
    grid.fit(train_X, train_Y)
    trained_clf = grid.best_estimator_
    #end of magic training!!!

    dataset = all_features[adjective][phase]
    dataset['adjective'] = adjective
    dataset['phase'] = phase
    dataset['classifier'] = trained_clf
    dataset['scaler'] = scaler
   
    test_set = all_features[adjective][phase]['test']
    test_X = scaler.transform(train_set['features'])
    test_Y = train_set['labels']
    train_score =  grid.best_score_
    test_score = f1_score(test_Y, trained_clf.predict(test_X))
    print "The training score is: %.2f, test score is %.2f" % (train_score, test_score)

    # Save the results in the folder
    with open(path_name, "w") as f:
        print "Saving file: ", path_name
        cPickle.dump(dataset, f, protocol=cPickle.HIGHEST_PROTOCOL)

train_adjective_phase_classifier = original_train_adjective_phase_classifier

def main():
    if len(sys.argv) == 6:
        path, adjective, phase, n_jobs, boost = sys.argv[1:]
        n_jobs = int(n_jobs)
        boost = bool(int(boost))
        print "Training the adjective %s for the phase %s" % (
                adjective, phase)

        loaded_features = load_adjective_phase(path)
        p = Parallel(n_jobs=n_jobs,verbose=0)
        p(delayed(train_adjective_phase_classifier)(path, adjective, phase, loaded_features, boost))

    elif len(sys.argv) == 5:
        path, adjective, n_jobs, boost = sys.argv[1:]
        n_jobs = int(n_jobs)
        boost = bool(int(boost))
        print "Training the adjective %s" % adjective
        loaded_features = load_adjective_phase(path)
 
        p = Parallel(n_jobs=n_jobs,verbose=0)
        p(delayed(train_adjective_phase_classifier)(path, adjective, phase, loaded_features, boost) 
            for phase in itertools.product(phases))
 
    elif len(sys.argv) == 4:
        path, n_jobs, boost = sys.argv[1:]
        n_jobs = int(n_jobs)
        boost = bool(int(boost))
        print "Training the all combinations of adjectives and phases"
        loaded_features = load_adjective_phase(path)
 
        p = Parallel(n_jobs=n_jobs,verbose=0)
        p(delayed(train_adjective_phase_classifier)(path, adjective, phase, loaded_features, boost) 
            for adjective, phase in itertools.product(adjectives,
                                                      phases))
    else:
        print "Usage:"
        print "%s path adjective phase n_jobs boosted" % sys.argv[0]
        print "%s path adjective n_jobs boosted" % sys.argv[0]
        print "%s path n_jobs boosted" % sys.argv[0]
        print "Path to the base directory, boosted is true/false for gradient boosting"

if __name__=="__main__":
    main()
    print "done"        

