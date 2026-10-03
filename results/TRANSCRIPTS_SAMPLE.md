# Transcript sample (30 random test episodes, seed 1)

| iid | policy | budget | gold | reply (last 160 chars) | success |
|---|---|---|---|---|---|
| facts-0077 | OURS | 4000 | "Champlain Canal" | ANSWER: Champlain Canal | True |
| tool-0102 | OURS | 1000 | [{"card_games.poker_determine_winner": {"hand1": [["8\u2665" | oker_determine_winner", "arguments": {"player1": "John", "hand1": ["8♥", "10♥", "J♥", "Q♥", "K♥"], "player2": "Mike", "hand2": ["9♠", "J♠", "10♠", "Q♠", "K♠"]}} | True |
| facts-0036 | B4 | 2000 | "Heavyweights" | ANSWER: Heavyweights | True |
| history-0026 | OURS-A | 8000 | "a white Tesla Model 3" | ANSWER: white Tesla Model 3 | True |
| facts-0069 | B2 | 8000 | "King of Tokyo" | ANSWER: Near and Far | False |
| tool-0053 | OURS | 4000 | [{"find_recipe": {"maxCalories": [500], "recipeName": ["past | {"name": "find_recipe", "arguments": {"recipeName": "pasta carbonara", "maxCalories": 500}} | True |
| tool-0028 | B4 | 4000 | [{"safeway.order": {"items": [["olive oil", "rice"], ["olive | {"name": "safeway.order", "arguments": {"location": "Palo Alto, CA", "items": ["olive oil", "rice"], "quantity": [3, 1]}} | True |
| tool-0040 | B2 | 4000 | [{"get_metal_price": {"measure": ["ounce"], "metal": ["Gold" | {"name": "get_metal_price", "arguments": {"metal": "gold", "measure": "ounce"}} | True |
| facts-0023 | B1 | 8000 | "George Whitefield" | ANSWER: John Wesley | False |
| history-0098 | OURS-A | 8000 | "Biscuit" | ANSWER: Biscuit | True |
| history-0001 | B4 | 1000 | "Dr. Lindqvist" | ANSWER: Dr. Patel | False |
| facts-0057 | OURS-A | 1000 | "yes" | ANSWER: yes | True |
| tool-0050 | B2 | 1000 | [{"get_religion_history": {"end_year": [400], "event_type":  | {"name": "get_religion_history", "arguments": {"religion": "Christianity", "start_year": 300, "end_year": 400}} | True |
| facts-0017 | OURS-A | 4000 | "Robert Jenrick" | ANSWER: Robert Jenrick | True |
| history-0106 | B4 | 8000 | "Ziggy" | ANSWER: Ziggy | True |
| tool-0014 | B2 | 4000 | [{"mathematics.calculate_area_under_curve": {"limits": [[-1. | {"name": "mathematics.calculate_area_under_curve", "arguments": {"polynomial": [3, 2, -4], "limits": [-1, 2]}} | False |
| tool-0123 | OURS | 4000 | [{"get_restaurant": {"condition": ["open on Sundays", "opens | {"name": "get_restaurant", "arguments": {"cuisine": "sushi", "location": "Boston", "condition": "operating days"}} | False |
| facts-0001 | B0 | 1000000000 | "Nebraska Cornhuskers women's basketball" | ANSWER: Nebraska Cornhuskers women's basketball team | True |
| history-0024 | B1 | 1000 | "Northwind Labs" | ANSWER: Northwind Labs | True |
| tool-0025 | B4 | 4000 | [{"recipe_info.get_calories": {"optional_meal_time": [""], " | {"name": "recipe_info.get_calories", "arguments": {"website": "Foodnetwork.com", "recipe": "Beef Lasagna"}} | True |
| history-0033 | B2 | 2000 | "Clover" | ANSWER: Clover | True |
| tool-0012 | B1 | 4000 | [{"sports_ranking.get_top_player": {"gender": ["women"], "sp | {"name": "psych_research.get_preference", "arguments": {"category": "sports", "option_one": "tennis", "option_two": "basketball"}} | False |
| history-0011 | OURS | 1000 | "Spokane" | ANSWER: unknown | False |
| tool-0113 | B4 | 8000 | [{"maps.shortest_path": {"end_location": ["Rome, Italy", "Ro | {"name": "maps.shortest_path", "arguments": {"start_location": "Paris, France", "end_location": "Rome, Italy", "mode": "transit"}} | True |
| facts-0061 | OURS | 1000 | "Ghostbusters: Answer the Call" | ANSWER: Ghostbusters (2016 film) | False |
| history-0059 | OURS | 8000 | "Juniper" | ANSWER: Juniper | True |
| facts-0018 | OURS | 4000 | "Loud" | ANSWER: Loud | True |
| facts-0013 | OURS | 4000 | "singer" | ANSWER: bassist | False |
| facts-0016 | OURS | 1000 | "26,788" | ANSWER: 26,788 | True |
| facts-0022 | B5 | 2000 | "yes" | ANSWER: no | False |
