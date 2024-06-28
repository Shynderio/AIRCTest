import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, MinMaxScaler

def load_data():
    # Load the dataset
    user_data = pd.read_csv('../data/raw/frappe_dataset.csv', sep="\t")
    # item_data = pd.read_csv('../data/raw/meta.csv', sep="\t")
    # item_features = ['item', 'package', 'category', 'downloads', 'developer', 'language', 'price', 'rating']
    # item_data = item_data[item_features]
    # merged_data = pd.merge(user_data, item_data, on='item')
    return user_data

def calculate_user_rate(row):
    if row['cnt'] == 1 and row['context_total_cnt'] == 1:
        return 50
    return (row['cnt'] / row['context_total_cnt']) * 100

def preprocess_data(data):
    context_columns = ['user', 'daytime', 'weekday', 'isweekend', 'homework', 'cost', 'weather', 'country', 'city']
    
    # Calculate the total cnt for each context
    data['context_total_cnt'] = data.groupby(context_columns)['cnt'].transform('sum')
    
    # Calculate user rate
    data['user_rate'] = data.apply(calculate_user_rate, axis=1)
    scaler = MinMaxScaler(feature_range=(-1, 1))
    data['user_rate'] = scaler.fit_transform(data['user_rate'].values.reshape(-1, 1))
    # Select relevant features
    features = ['user', 'item', 'daytime', 'weekday', 'isweekend', 'homework', 'cost', 'weather', 
                'country', 'city', 'user_rate']
    data = data[features]
    
    return data

def encode_data(data):
    # Prepare the encoder
    categorical_features = ['user', 'item', 'daytime', 'weekday', 'isweekend', 'homework', 'cost'
                            'weather', 'country', 'city']
    encoder = OneHotEncoder(sparse=False)
    encoded_features = encoder.fit_transform(data[categorical_features])
    
    # Create a DataFrame with encoded features
    encoded_df = pd.DataFrame(encoded_features, columns=encoder.get_feature_names(categorical_features))
    
    # Combine with numeric features and the target variable
    numeric_features = data[[ 'user_rate']]
    final_data = pd.concat([encoded_df, numeric_features], axis=1)
    
    return final_data

def split_data(data):
    train_data, temp_data = train_test_split(data, test_size=0.4, random_state=42)
    val_data, test_data = train_test_split(temp_data, test_size=0.5, random_state=42)
    return train_data, val_data, test_data

def save_to_libfm(data, filename):
    with open(filename, 'w') as f:
        for index, row in data.iterrows():
            label = row['user_rate']
            features = row.drop('user_rate')
            feature_str = " ".join([f"{i+1}:{val}" for i, val in enumerate(features) if val != 0])
            f.write(f"{label} {feature_str}\n")

if __name__ == "__main__":
    data = load_data()
    data = preprocess_data(data)
    data = encode_data(data)
    
    train_data, val_data, test_data = split_data(data)
    
    save_to_libfm(train_data, "../data/processed/frappe.train.libfm")
    save_to_libfm(val_data, "../data/processed/frappe.validation.libfm")
    save_to_libfm(test_data, "../data/processed/frappe.test.libfm")
