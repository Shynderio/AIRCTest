import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder

def load_data():
    # Load the dataset
    user_data = pd.read_csv('../data/raw/frappe_dataset.csv', sep="\t")
    item_data = pd.read_csv('../data/raw/meta.csv', sep="\t")
    item_features = ['item', 'package', 'category', 'downloads', 'developer', 'language', 'price', 'rating']
    item_data = item_data[item_features]
    merged_data = pd.merge(user_data, item_data, on='item')
    return merged_data

def calculate_rating(row):
    if row['cnt'] == 1 and row['context_total_cnt'] == 1:
        return 50
    return (row['cnt'] / row['context_total_cnt']) * 100

def preprocess_data(data):
    context_columns = ['user', 'daytime', 'weekday', 'isweekend', 'homework', 'cost', 'weather', 'country', 'city']
    
    # Calculate the total cnt for each context
    data['context_total_cnt'] = data.groupby(context_columns)['cnt'].transform('sum')
    
    # Apply the rating function
    data['user_rate'] = data.apply(calculate_rating, axis=1)
    
    # Encode the data
    data = encode_data(data)
    
    # Drop 'cnt' and 'context_total_cnt' as they are not needed for the model
    data.drop(columns=['cnt', 'context_total_cnt'], inplace=True)
    
    return data

def encode_data(data):
    features = ['user', 'item', 'daytime', 'weekday', 'isweekend', 'homework', 'weather', 'country', 'city', 
                'package', 'category', 'downloads', 'developer', 'language', 'price', 'rating', 'user_rate']
    data = data[features]
    print(data.shape)
    encoder = OneHotEncoder()
    encoder.fit(data.drop(columns=['user_rate']))  # Exclude 'user_rate' from encoding

    encoded_data = []
    for row in data.iterrows():
        transformed_data = encoder.transform([row[1].drop('user_rate')]).toarray()
        converted_data = []
        for i in range(len(transformed_data[0])):
            if transformed_data[0][i] == 1:
                converted_data.append(i)
        converted_data.append(row[1]['user_rate'])  # Append 'user_rate' as the last feature
        encoded_data.append(converted_data)
    
    return pd.DataFrame(encoded_data)

def split_data(data):
    train_data, temp_data = train_test_split(data, test_size=0.4, random_state=42)
    val_data, test_data = train_test_split(temp_data, test_size=0.5, random_state=42)
    
    return train_data, val_data, test_data

def save_to_libfm(data, filename):
    with open(filename, 'w') as f:
        for index, row in data.iterrows():
            label = row[-1]  # The last column is the label (user_rate)
            features = row[:-1]
            feature_str = " ".join([f"{i}:{1}" for i, v in enumerate(features) if v != 0])
            f.write(f"{label} {feature_str}\n")

if __name__ == "__main__":
    data = load_data()
    processed_data = preprocess_data(data)
    train_data, val_data, test_data = split_data(processed_data)
    
    save_to_libfm(train_data, "../data/processed/train_data.libfm")
    # save_to_libfm(val_data, "../data/processed/val_data.libfm")
    # save_to_libfm(test_data, "../data/processed/test_data.libfm")
