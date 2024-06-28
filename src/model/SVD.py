from surprise import Dataset, Reader
from surprise import SVD
from surprise.model_selection import cross_validate, train_test_split

# Load your dataset into Surprise format (replace 'ml-100k' with your dataset)
data = Dataset.load_builtin('ml-100k')

# Split data into train and test sets (optional)
trainset, testset = train_test_split(data, test_size=0.25)

# Choose SVD algorithm
algo = SVD()

# Train the algorithm on the trainset
algo.fit(trainset)

# Example: Get top-N recommendations for a specific user (user id 1)
user_id = '1'
top_n = algo.top_n(user_id, n=10)  # Get top 10 recommendations for user 1

# Print top-N recommendations
for uid, user_ratings in top_n.items():
    print(f"User {uid}:")
    for iid, rating in user_ratings:
        print(f"Item {iid} (predicted rating: {rating})")

# Optionally, evaluate the model
cross_validate(algo, data, measures=['RMSE', 'MAE'], cv=5, verbose=True)
