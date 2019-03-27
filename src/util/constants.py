"""
Constants applicable to running integration tests against local nodes.
"""


# These must match constants from the commands/bin/env.sh file for localnet node 0 and 1.
LOCALNET0_CHAOS_RPC = 26670
LOCALNET0_NDAU_RPC = 26671
LOCALNET1_CHAOS_RPC = 26672
LOCALNET1_NDAU_RPC = 26673

# The identity that the chaos tool uses to map to the system namespace for gets and sets.
SYSVAR_IDENTITY = "sysvar"
BPC_ACCOUNT = "bpc-operations"
SYSVAR_NAMESPACE_B64 = "A2etqqaA3qQExilg+ywQ4ElRsyoDJh9lR5A+Thg5PcTR"

# Sysvar keys.
ACCOUNT_ATTRIBUTES_KEY = "AccountAttributes"
EAI_FEE_TABLE_KEY = "EAIFeeTable"
TRANSACTION_FEE_SCRIPT_KEY = "TransactionFeeScript"

# For use when changing tx fees throughout the integration tests.
ZERO_FEE_SCRIPT = '"oAAgiA=="'
ONE_NAPU_FEE_SCRIPT = '"oAAaiA=="'
ONE_NAPU_FEE = 1

# BPC addresses and keys, created deterministically using the 12 eyes with account recovery.
BPC_ADDRESS = "ndakj49v6nnbdq3yhnf8f2j6ivfzicedvfwtunckivfsw9qt"
BPC_ROOT_PUBLIC_KEY = "npuba4jaftckeeb4eb3ur3ubmg38skak7bbinycna8dudjx8ka7emzjpx4bvpzp43daaaaaaaaaaaaak9srd4ru8uj3rsmxghk32jfmkjgqvrff2s6axjrqyyn9h7fetzr7rndpaec3k"
BPC_ROOT_PRIVATE_KEY = "npvta8jaftcjebhe9pi57hji5yrt3yc3f2gn3ih56rys38qxt52945vuf8xqu4jfkaaaaaaaaaaaacz6d28v6zwuqm6c7jt4yqcjk4ujvw53jqehafkm5xxvh39jjep58u7pw33dd7cc"
BPC_OWNERSHIP_PUBLIC_KEY = "npuba4jaftckeebyrmpkw4ap7jae22wyb83ncdseuwpvfibunh5fi8id6vs2he86jwieh856caaaaaasjfhkhw6npur6sgxy3r5b4i2hxhqia3w9dm2kz8tgkgf5k5jm88c5htkhhpt8"
BPC_OWNERSHIP_PRIVATE_KEY = "npvta8jaftcjea9en4tr26txweh3fkejikikubnn7mthymvir3292cquaphxr2egybb9y9asaaaaaecjj4t7hddnv9ebxpym82qugb7j5uagph248cx9wjuttq4y4k9zs43vvnn3z9tw"
BPC_VALIDATION_PUBLIC_KEY = "npuba4jaftckeeb2dehw5ck56sudrc5ws8rhgb48kftzgsze7rfrsfrfpbq8uykyzyiib8fk4aaaaaa2qacs9zwpmpje56fz6xhj2u5ekjght9ckx5zhgz4xsw7fh46xbsubryzh6s9k"
BPC_VALIDATION_PRIVATE_KEY = "npvta8jaftcjeb8b7f3hkxv3u3zgqwq7q9dp4jjfpihkbp38iut642b5eyzr2rgtgcartkysaaaaagdsawh77dk5kjg9bp9fj4qey3cujt6r2uxq733x8xnfhjj8zfinese7xjui29vu"
