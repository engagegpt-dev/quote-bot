from web_interface import parse_accounts_from_text

sample = '''Account 1:
  Username: ladybmhaga
  Password: 9fGGZTQtuT
  Email: teresajohnson@hyperpasmf.com
  Auth Token: ac3d91d00637ef7f5557398c369c48c62b02e1a2
  TOTP Secret: LKU2J5OEYDAWJH4Q
  Registration Year: 2015
------------------------------

Account 2:
  Username: youskoodu95
  Password: pzAnb2DCBC
  Email: davidupshaw@achrosmf.com
  Auth Token: 9540732f5badcacfc744f6a3fef97a07644d7d68
  TOTP Secret: 27UKKMEZKFAHNNMY
  Registration Year: 2015
'''

parsed = parse_accounts_from_text(sample)
print('Parsed', len(parsed), 'accounts')
for p in parsed:
    print(p)
