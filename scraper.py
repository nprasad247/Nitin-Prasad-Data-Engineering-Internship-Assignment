import pandas as pd
import wikipedia as wiki
import requests
import re
import unicodedata

# Specify the number of cities in the table
num = int(input('How many cities? (Limit: 311) '))
filename = input('Save CSV as (Enter filename here): ').replace('.csv', '') + '.csv'
while num < 0 or num > 311:
    num = int(input('Invalid Value: Enter a new number'))


# Function to generate a table from a Wikipedia article.
def generate_table(title, table_num):
    page = requests.get('https://en.wikipedia.org/wiki/' + title.replace(' ', '_'))
    return pd.read_html(page.text.encode("UTF-8"))[table_num]


# Search a table for a specific query, returning the row of the table if the query is found, else 'None'.
# Supports exact and inexact matches.
def keyword_search(tab, query, exact=False):
    
    def mask(column):
        m = [tab.iloc[i, column] == query for i in range(len(tab))] if exact else tab.iloc[:, column].str.contains(
            query)
        # Get rid of NaNs
        for i, n in enumerate(m):
            if type(n) != bool:
                m[i] = False
        return m

    names = tab[mask(0)]
    i = 1
    # If not in the first column, search the rest
    while len(names) == 0 and i < len(tab.iloc[0]):
        names = tab[mask(i)]
        i += 1
    if len(names) == 0:
        return 'None'
    return names


# Utility function to clean up names joined together
def split_upper(s):
    if " " in s:
        return s
    result = ""
    prevchar = ""
    for char in s:
        if char.isupper() and prevchar.islower():
            result += " " + char
        else:
            result += char
        prevchar = char
    return ", ".join(result.split())


def clean_mayors(s):
    # regex pattern to find lowercase next to uppercase
    splits = re.findall(r'[a-z][A-Z]', s)
    words = re.split(r'[a-z][A-Z]', s, maxsplit=1)
    if not splits:
        # regex pattern to find ')' next to uppercase letter
        splits = re.findall(r'\)[A-Z]', s)
        words = re.split(r'\)[A-Z]', s, maxsplit=1)
    # LaToya is the sole exception to the rule
    if not splits or 'LaToya' in s:
        return s
    # Remove 'Mayor' from name
    return (words[0] + splits[0][0]).replace('Mayor', '')


# Generate the initial table from the Wikipedia page
table = generate_table('List_of_United_States_cities_by_population', 4).iloc[:num]

# Clean up the column names
table.columns = ['Rank (2017)', 'City', 'State', 'Population Estimate (2017)', '2010 Census', 'Change', '2016 Land Area', '2016 Land Area (km)', '2016 Population Density', '2016 Population Density (km)', 'Location']

# Clean up the city names, removing reference tags from the text
for i, name in enumerate(table['City']):
    if '[' in name:
        table.replace(name, name[:name.index('[')], inplace = True)
# Outlier: Modify for search purposes
table.replace('Clinton', 'Clinton Township', inplace = True)

# Remove redundant columns
del table['2016 Land Area (km)']
del table['2016 Population Density (km)']

# Cleanup for several values in the table, removing stray Unicode characters and reformatting numerical values
for i, a in enumerate(table.iloc[:,6]):
    table.replace(table.iloc[:,5][i], unicodedata.normalize('NFKD', table.iloc[:,5][i]).replace('−','-'), inplace = True)
    table.replace(table.iloc[:,6][i], float(a.replace('\xa0sq\xa0mi', '').replace(',', '')), inplace = True)
    table.replace(table.iloc[:,7][i], table.iloc[:,7][i].replace('/sq\xa0mi', '').replace(',', ''), inplace = True)
    coors = table.iloc[:,8][i]
    numerical = re.findall(r'[0-9]+.[0-9]+', coors[coors.index('/') + 1:])
    table.replace(coors, "({}, {})".format(*numerical), inplace = True)
cities = table['City']
states = table['State']
# Gathering nicknames, counties, and mayor for each city
nicknames = []
counties = []
mayors = []
for i in range(num):
    loc = "{}, {}".format(cities[i], states[i])
    title = wiki.search(loc)[0]
    print('Parsing data for: ' + loc)
    city_table = generate_table(title, 0)
    j = 1
    # Find the correct table
    while 0 in city_table:
        city_table = generate_table(title, j)
        j += 1
    # Remove 'City' from title for search purposes
    title = title.replace(' City', "")
    names = keyword_search(city_table, 'Nickname')
    if names is 'None':
        nicknames.append(names)
    else:
        names = names.iloc[0, 0]
        # Clean up the nickname, choosing the first nickname given
        if '(s)' in names:
            name = unicodedata.normalize("NFKD", names[13:].split(',')[0].split(';')[0])
        else:
            name = unicodedata.normalize("NFKD", names[10:].split(',')[0].split(';')[0])
        if "[" in name:
            name = name[:name.index('[')]
        if "(official)" in name:
            name = name[:name.index('(')]
        nicknames.append(name)
    # County may be stored under multiple possible keys
    county = keyword_search(city_table, 'County', True)
    if county is 'None':
        county = keyword_search(city_table, 'Counties', True)
    if county is 'None':
        county = keyword_search(city_table, 'counties')
    if county is 'None':
        county = cities[i]

    if type(county) != str:
        # Cleanup: Remove all [...] and separate words
        county = split_upper(re.sub(r'\[[^\]]*\]', '', county.iloc[0, 1]))
    counties.append(county)
    mayor = keyword_search(city_table, 'Mayor')
    if mayor is 'None':
        mayor = keyword_search(city_table, 'City council')
    if mayor is 'None':
        mayors.append('N/A')
    else:
        mayors.append(clean_mayors(re.sub(r'\[[^\]]*\]', '', mayor.iloc[0, 1])))
# New York county abnormality, clean up
counties[0] = ", ".join(counties[0].split(')'))
# Add the new columns to the table
table.insert(3, 'Nickname', nicknames)
table.insert(2, 'Counties', counties)
table.insert(4, 'Mayor', mayors)
# Manually clean up the few remaining abnormalities
table.replace('See Nicknames of New York City', 'The Big Apple', inplace=True)
table.replace('See List of nicknames for San Francisco', 'SF', inplace=True)
table.replace('See Nicknames of Boston', 'The Cradle of Liberty', inplace=True)

# Save the table to CSV
table.to_csv(filename)
print('File saved as ' + filemame)
