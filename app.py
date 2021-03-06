from flask import Flask, render_template, send_from_directory
app = Flask(__name__)
import datetime
import pickle
import os
import os.path
from explorer import Model

import numpy as np
from flask import Flask, request, send_from_directory, jsonify

from scripts.download_from_s3_bucket import download_file_from_s3

default_n = 15
STATIC_DIR = os.path.dirname(os.path.realpath(__file__)) + '/public'
CACHE = {}

#app = Flask(__name__, static_folder='public', static_url_path='')

@app.route('/')
def index():
    return render_template("index.html")

@app.route("/paper-embedding-proximity-page")
def paper_embedding_table():
    return render_template('paper_embedding_proximity.html')

@app.route("/paper-embedding-viz")
def paper_embedding_viz():
    return render_template('paper_embedding_viz.html')

@app.route("/word-embedding-proximity")
def get_word_embedding_proximity():
    # query params
    n = int(request.args.get('n', default_n))
    input_str = request.args.get('input_str')
    selected_word_embedding = request.args.get('type')

    input_str = input_str.lower()

    # inputted_word = inputted_word.strip().lower() # todo both upper and lower case atm. find lowercase version if not found
    # inputted_word = inputted_word.replace(' ', '_') # todo probably keep
    # fuzzy match similar ones!!!!! and show

    print('Inputted string: {}. Embedding type: {}'.format(input_str, selected_word_embedding))

    if selected_word_embedding == 'gensim':
        gensim_labels_lowercase_strip = [x.lower().strip() for x in gensim_labels]
        if input_str in gensim_labels_lowercase_strip:
            print('Words most similar to:', input_str)
            similar_words, distances, sorted_idx = get_closest_vectors(gensim_labels, gensim_embeddings,
                                                           gensim_label_to_embeddings[input_str], n=n)
            response = [{'label': word, 'distance': round(float(dist), 5)} for word, dist in
                        zip(similar_words, distances)]
            print(response)
        else:
            response = ['Word not found']
    # elif selected_word_embedding == 'fast_text':
    #     if inputted_word in fast_text_labels:
    #         print('Words most similar to:', inputted_word)
    #         similar_words, distances = get_closest_vectors(fast_text_labels, fast_text_embeddings,
    #                                                        fast_text_label_to_embeddings[inputted_word], n=15)
    #         response = [{'word': word, 'distance': round(float(dist), 5)} for word, dist in
    #                     zip(similar_words, distances)]
    #         print(response)
    #     else:
    #         response = 'Word not found'
    else:
        response = 'Selected wrong word embedding'

    return jsonify(response)

@app.route("/paper-embedding-proximity")
def get_paper_embedding_proximity():
    print('Within paper embedding proximity table get ')
    # query params
    n = int(request.args.get('n', default_n))
    input_str = request.args.get('input_str')
    selected_embedding = request.args.get('type')

    input_str_clean = input_str.lower().strip()

    print('Inputted string: {}.\nInputted string clean: {}. Embedding type: {}'.format(input_str, input_str_clean, selected_embedding))

    if selected_embedding == 'lsa':
        lsa_labels_lowercase = [x.lower().strip() for x in lsa_labels]
        if input_str_clean in lsa_labels_lowercase:
            print('Labels most similar to:', input_str)
            similar_papers, distances, sorted_idx = get_closest_vectors(lsa_labels, lsa_embeddings,
                                                           lsa_label_to_embeddings[input_str], n=n)
            response = [{'label': label, 'distance': round(float(dist), 5)} for label, dist in
                        zip(similar_papers, distances)]
            print(response)
        else:
            response = ['Paper not found']
    elif selected_embedding == 'doc2vec':
        doc2vec_labels_lowercase = [x.lower().strip() for x in doc2vec_labels]
        if input_str_clean in doc2vec_labels_lowercase:
            print('Labels most similar to:', input_str)
            similar_words, distances, sorted_idx = get_closest_vectors(doc2vec_labels, doc2vec_embeddings,
                                                           doc2vec_label_to_embeddings[input_str], n=n)
            response = [{'label': word, 'distance': round(float(dist), 5)} for word, dist in
                        zip(similar_words, distances)]
            print(response)
        else:
            response = ['Paper not found']
    else:
        response = 'Selected wrong embedding'

    return jsonify(response)

@app.route("/get-embedding-labels")
def get_embedding_labels():
    selected_embedding = request.args.get('embedding_type', 'gensim')
    if selected_embedding == 'gensim':
        labels = gensim_labels
    elif selected_embedding == 'lsa':
        labels = lsa_labels
    elif selected_embedding == 'doc2vec':
        labels = doc2vec_labels
    else:
        labels = ['embedding_type not found']

    return jsonify(labels)

@app.route("/search-papers")
def search_papers():
    query = request.args.get('query', '')
    selected_embedding = request.args.get('c', 'lsa')

    if selected_embedding == 'tfidf':
        # features = doc_tfidf_features # todo use internal tfidf?
        pass
    elif selected_embedding == 'lsa':
        model = lsa_IR_model
        # features = doc_lsa_features
    else:
        labels = ['embedding_type not found']

    preprocessed_query = query.lower()
    print('Searching for query: {}'.format(preprocessed_query))
    query_feats = model['model'].transform([preprocessed_query])

    closest_papers_titles, distances, sorted_indices = get_closest_vectors(model['titles'],
                                                                           model['feats'],
                                                                           query_feats, n=100)

    print('Closest paper titles top 5: {}'.format(closest_papers_titles[0:5]))
    top_paper_ids = np.array(model['ids'])[sorted_indices]

    response_obj = [{'title': title, 'paper_id': paper_id, 'distance': round(distance, 4)} for title,
                        paper_id, distance in zip(closest_papers_titles, top_paper_ids, distances)]

    return jsonify(response_obj)

@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory('public/js', path)

@app.route('/styles/<path:path>')
def send_styles(path):
    return send_from_directory('public/styles', path)

@app.route("/api/explore")
def explore():
    query = request.args.get('query', '')
    limit = request.args.get('limit', '1000')
    enable_clustering = 'True'
    num_clusters = request.args.get('num_clusters', '30')
    embedding_type = request.args.get('embedding_type', 'gensim')

    if embedding_type == 'gensim':
        embedding_model = gensim_embedding_model
    elif embedding_type == 'lsa':
        embedding_model = lsa_embedding_model
    elif embedding_type == 'doc2vec':
        embedding_model = doc2vec_embedding_model
    else:
        embedding_model = gensim_embedding_model  # default model so it doesn't crash

    print('Embedding type: {}. embedding_model: {}'.format(embedding_type, embedding_model))

    cache_key = '-'.join([query, limit, enable_clustering, num_clusters, embedding_type])
    result = CACHE.get(cache_key, {})
    if len(result) > 0:
        return jsonify({'result': CACHE[cache_key], 'cached': True})
    try:
        exploration = embedding_model.explore(query, limit=int(limit))
        exploration.reduce()
        if len(enable_clustering):
            if (len(num_clusters)):
                num_clusters = int(num_clusters)
            exploration.cluster(num_clusters=num_clusters)
        result = exploration.serialize()
        CACHE[cache_key] = result
        return jsonify({'result': result, 'cached': False})
    except KeyError:
        return jsonify({'error': {'message': 'No vector found for ' + query}})

@app.route("/api/compare")
def compare():
    limit = request.args.get('limit', 100)
    queries = request.args.getlist('queries[]')
    # queries = request.args.get('queries') # todo double check all browsers
    # queries = queries.split(';')
    embedding_type = request.args.get('embedding_type', 'gensim')
    print(limit)
    print(queries)

    if embedding_type == 'gensim':
        embedding_model = gensim_embedding_model
    elif embedding_type == 'lsa':
        embedding_model = lsa_embedding_model
    elif embedding_type == 'doc2vec':
        embedding_model = doc2vec_embedding_model
    else:
        embedding_model = gensim_embedding_model  # default model so it doesn't crash

    print('Embedding type: {}. embedding_model: {}'.format(embedding_type, embedding_model))

    try:
        # for i in range(len(queries)):
        #     queries[i] = queries[i].strip().lower()
        #       if embedding_model is word_embedding_model:
        #       queries[i] = queries[i].replace(' ', '_')
        result = embedding_model.compare(queries, limit=int(limit))
        return jsonify({'result': result})
    except KeyError:
        return jsonify({'error':
                            {'message': 'No vector found for {}'.format(queries)}})

# --------------------
# Helper functions
# --------------------

def get_closest_vectors(labels, all_vectors, query_vector, n=5):
    distances = np.linalg.norm(all_vectors - query_vector, axis=1)  # vectorised # todo try scikit
    sorted_idx = np.argsort(distances)

    return list(np.array(labels)[sorted_idx][0:n]), list(distances[sorted_idx][0:n]), sorted_idx[0:n]

def get_model_obj(model_object_path):
    print('Loading embeddings at path: {}'.format(model_object_path))
    with open(model_object_path, 'rb') as handle:
        model_obj = pickle.load(handle, encoding="latin1")
        # labels = model_obj['labels']
        # embeddings = model_obj['embeddings']
        # label_to_embeddings = {label: embeddings[idx] for idx, label in
        #                        enumerate(labels)}
        print('Num ids: {}'.format(len(model_obj['ids'])))
        print('Num titles: {}'.format(len(model_obj['titles'])))
        print('feats shape: {}'.format(model_obj['feats'].shape))
        print('Model: {}'.format(model_obj['model']))
        model_obj['model'].named_steps.tfidf_vectorizer.input = 'content'

        return model_obj

def get_embedding_objs(embedding_path):
    print('Loading embeddings at path: {}'.format(embedding_path))
    with open(embedding_path, 'rb') as handle:
        embedding_obj = pickle.load(handle, encoding="latin1")
        labels = embedding_obj['labels']
        embeddings = embedding_obj['embeddings']
        label_to_embeddings = {label: embeddings[idx] for idx, label in
                                      enumerate(labels)}
        print('Num vectors: {}'.format(len(labels)))

        return labels, embeddings, label_to_embeddings

def download_model(key, output_path):
    """
    Function downloads necessary files from S3 bucket on server startup
    :param key: path within S3 bucket to get model
    :param output_path: where to store the downloaded model

    """
    print("Looking fro model in {}".format(output_path))
    if os.path.exists(output_path):
        print('File at: {} already exists'.format(output_path))
    else:
        download_file_from_s3(key, output_path)

# All models and saved objects
# ------------------
# gensim word2vec word embeddings (2d + 100d)
# fastText word embeddings
# LSA paper paper embeddings (2d + 100d + 300d)
# doc2vec paper embeddings (2d + 100d)
# ------------------

# Download all models if they don't already exist (download_model() checks)
# todo should be done in another script so 4 workers dont do it as well
gensim_embedding_name = 'type_word2vec#dim_100#dataset_ArxivNov4#time_2018-11-13T07_17_46.600182'
gensim_2d_embeddings_name = 'type_word2vec#dim_2#dataset_ArxivNov4#time_2018-11-13T07_17_46.600182'
lsa_embedding_name = 'lsa-100.pkl' # 'lsa-300.pkl' # seems too big
lsa_embedding_2d_name = 'lsa-2.pkl'
lsa_IR_model_object_name = 'lsa-tfidf-pipeline-50k-feats-400-dim.pkl'
doc2vec_embedding_name = 'type_doc2vec#dim_100#dataset_ArxivNov4#time_2018-11-14T02_10_25.587584' # 'doc2vec-300.pkl' # not right format
doc2vec_embedding_2d_name = 'type_doc2vec#dim_2#dataset_ArxivNov4#time_2018-11-14T02_10_25.587584'

gensim_embedding_path = 'data/word_embeddings/' + gensim_embedding_name
gensim_2d_embeddings_path = 'data/word_embeddings/' + gensim_2d_embeddings_name
lsa_embedding_path = 'data/paper_embeddings/' + lsa_embedding_name
lsa_embedding_2d_path = 'data/paper_embeddings/' + lsa_embedding_2d_name
lsa_IR_model_object_path = 'data/models/' + lsa_IR_model_object_name
doc2vec_embedding_path = 'data/paper_embeddings/' + doc2vec_embedding_name
doc2vec_embedding_2d_path = 'data/paper_embeddings/' + doc2vec_embedding_2d_name

print('Beginning to download all models')
download_model('model_objects/' + gensim_embedding_name, gensim_embedding_path)
download_model('model_objects/' + gensim_2d_embeddings_name, gensim_2d_embeddings_path)
download_model('model_objects/' + lsa_embedding_name, lsa_embedding_path)
download_model('model_objects/' + lsa_embedding_2d_name, lsa_embedding_2d_path)
#download_model('model_objects/' + lsa_IR_model_object_name, lsa_IR_model_object_path)
download_model('model_objects/' + doc2vec_embedding_name, doc2vec_embedding_path)
download_model('model_objects/' + doc2vec_embedding_2d_name, doc2vec_embedding_2d_path)

# Loading models into embedding objects and Explorer objects
# Load all word embeddings
gensim_labels, gensim_embeddings, gensim_label_to_embeddings = get_embedding_objs(gensim_embedding_path)

# Load gensim 2d embedding model into word2vec-explorer visualisation
gensim_embedding_model = Model(gensim_2d_embeddings_path)

# fast_text_embedding_path = 'data/word_embeddings/fast_text_vectors.pkl'
# print('Loading fast_text vectors at path: {}'.format(fast_text_embedding_path))
# fast_text_labels, fast_text_embeddings, fast_text_label_to_embeddings = get_embedding_objs(fast_text_embedding_path)

# Load paper embeddings
lsa_labels, lsa_embeddings, lsa_label_to_embeddings = get_embedding_objs(lsa_embedding_path)
doc2vec_labels, doc2vec_embeddings, doc2vec_label_to_embeddings = get_embedding_objs(doc2vec_embedding_path)

# Load lsa model (2d TSNE-precomputed) into word2vec-explorer visualisation
lsa_embedding_model = Model(lsa_embedding_2d_path)

# Load doc2vec model (2d TSNE-precomputed) into word2vec-explorer visualisation
doc2vec_embedding_model = Model(doc2vec_embedding_2d_path)

# Load IR model objects for Information Retrieval
# lsa_IR_model = get_model_obj(lsa_IR_model_object_path)

if __name__ == '__main__':
    print('Server has started up at time: {}'.format(datetime.datetime.now().
                                                     strftime("%I:%M%p on %B %d, %Y")))
    app.run(debug=True, use_reloader=True) # not run for production. # host=0.0.0.0. port=80

