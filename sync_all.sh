cp sync_all.sh /tmp
hg update default
hg pull http://hg.tryton.org/trytond
cd trytond/modules
cp __init__.py ../tmp__init__
rm -r *

hg clone http://hg.tryton.org/modules/account
rm -r account/.hg
rm -r account/.hgtags

hg clone http://hg.tryton.org/modules/account_invoice
rm -r account_invoice/.hg
rm -r account_invoice/.hgtags

hg clone http://hg.tryton.org/modules/account_payment
rm -r account_payment/.hg
rm -r account_payment/.hgtags

hg clone http://hg.tryton.org/modules/account_product
rm -r account_product/.hg
rm -r account_product/.hgtags

hg clone http://hg.tryton.org/modules/bank
rm -r bank/.hg
rm -r bank/.hgtags

hg clone http://hg.tryton.org/modules/company
rm -r company/.hg
rm -r company/.hgtags

hg clone http://hg.tryton.org/modules/country
rm -r country/.hg
rm -r country/.hgtags

hg clone http://hg.tryton.org/modules/currency
rm -r currency/.hg
rm -r currency/.hgtags

hg clone http://hg.tryton.org/modules/party
rm -r party/.hg
rm -r party/.hgtags

hg clone http://hg.tryton.org/modules/party_relationship
rm -r party_relationship/.hg
rm -r party_relationship/.hgtags

hg clone http://hg.tryton.org/modules/party_siret
rm -r party_siret/.hg
rm -r party_siret/.hgtags

hg clone http://hg.tryton.org/modules/product
rm -r product/.hg
rm -r product/.hgtags

mv ../tmp__init__ __init__.py
rm /tmp/sync_all.sh
