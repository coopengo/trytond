SEP=------------------------------------------------

EXPECTED_ARGS=1
if [ $# -ne $EXPECTED_ARGS ]
then
    echo $SEP
    echo Usage:
    echo First argument : tag or branch to sync
    echo $SEP
    exit 0
fi

hg update default
hg pull http://hg.tryton.org/trytond
cd trytond/modules
cp __init__.py ../tmp__init__
rm -r *

declare -a modules=(
    "account"
    "account_invoice"
    "account_dunning"
    "account_dunning_letter"
    "account_payment"
    "account_payment_sepa"
    "account_payment_sepa_cfonb"
    "account_payment_clearing"
    "account_product"
    "account_statement"
    "bank"
    "company"
    "country"
    "currency"
    "party"
    "party_relationship"
    "party_siret"
    "product"
    "commission"
    "commission_waiting"
    )
for module in "${modules[@]}"
    do echo "$module"
    hg clone http://hg.tryton.org/modules/"$module"
    cd "$module"
    hg update "$1"
    rm -r .hg
    rm -r .hgtags
    cd ..
done

mv ../tmp__init__ __init__.py
