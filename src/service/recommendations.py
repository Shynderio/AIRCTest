from model.IFM import infer 
from scipy import stats
hidden_factors = [8, 256]


class RecommendationService:

    def __init__(self, db):
        self.db = db

    def get_recommendations(self, user_id, contexts):
        # Example function to get recommendations based on user_id and context
        # Implement your recommendation logic here
        pretrain_path = '../pretrain/fm_frappe_256/frappe_256'
        path = '../data/'
        dataset = 'frappe'
        
        data_instance = []
        # data_instance = [2, 1, 'morning', 'monday', 'workday', 'home', 'sunny', 'Spain', 0]
        data_instance.append(int(user_id))
        data_instance.append(1)
        # print(contexts)

        for context in contexts:
            data_instance.append(context['value'])

        # print(data_instance)
        result = infer(path, dataset, pretrain_path, data_instance, 3)
        result = result  - 957

        items = self.db.items.find({'item': {'$in': result.tolist()}})
        # items = []
        # explanations = []
        # for item in result:
            # items.append(self.db.items.find_one({'item': int(item)}))
            # explanations.append(self.explain_recommendation(int(item), contexts))

        # print(explanations)
        return items

    # def compute_oic(self, item_id, context, context_value):
    #     # Number of interactions where item is equal to item_id and context is equal to context_value
    #     return self.db['interactions'].count_documents({'item': item_id, context: context_value})

    # def compute_eic(self, item_id, context, context_value):
    #     # Number of interactions where context is equal to context_value
    #     Nc = self.db['interactions'].count_documents({context: context_value})
    #     # Number of interactions where item is equal to item_id
    #     Ni = self.db['interactions'].count_documents({'item': item_id})
    #     # Total number of interactions
    #     N = self.db['interactions'].count_documents({})
    #     return (Nc * Ni) / N

    # def compute_chi_square(self, item_id, context, context_value):
    #     Oic = self.compute_oic(item_id, context, context_value)
    #     Eic = self.compute_eic(item_id, context, context_value)
    #     if Eic == 0:
    #         return 0  # Avoid division by zero
    #     chi_square_stat = ((Oic - Eic) ** 2) / Eic
    #     df = self.db[context].count_documents({}) - 1
    #     # Compute p-value
    #     p_value = 1 - stats.chi2.cdf(chi_square_stat, df)
    #     return chi_square_stat, p_value
    
    # def explain_recommendation(self, item_id, contexts):
    #     chi_square_values = {}
    #     for context in contexts:
    #         print(context)
    #         chi_square_stat, p_value = self.compute_chi_square(item_id, context['type'], context['value'])
    #         # if p_value < 0.3:
    #         chi_square_values[context['type']] = (context['value'], p_value)

    #     sorted_contexts = sorted(chi_square_values.items(), key=lambda x: x[1][1])[:3]  # Sort by p-value and take top 3
    #     # explanations = {context['type']: context['value'] for context['type'], context['value'] in sorted_contexts}
    #     return sorted_contexts