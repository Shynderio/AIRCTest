import pandas as pd
from sklearn.preprocessing import OneHotEncoder, StandardScaler

def load_data():
    # Load the dataset
    user_data = pd.read_csv('../data/raw/frappe_dataset.csv', sep="\t")
    return user_data


def convertData(data):
    df = load_data()
    context_features = ['user','item','daytime', 'weekday', 'isweekend', 'homework', 'weather', 'country', 'city']
    encoder = OneHotEncoder()
    encoder.fit(df[context_features])
    transformed_data = encoder.transform([data])
    transformed_data = transformed_data.toarray()

    converted_data = []

    for i in range(len(transformed_data[0])):
        if transformed_data[0][i] == 1:
            converted_data.append(i)
    print("Converted Data: ", converted_data)
    # print("Encoder Categories:\n", encoder.categories_)
    Y = []
    X = []
    # for i in range(4082):
    #     Y.append(1.0*float(0))

    #     for item in data:
    #         X_i.append(item)
        
    return X, Y

data_instance = [1, 1, 'morning', 'monday', 'workday', 'home', 'sunny', 'Spain', 0]

convertData(data_instance)