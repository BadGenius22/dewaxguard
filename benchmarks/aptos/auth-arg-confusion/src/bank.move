module benchmark::bank {
    use std::signer;
    use aptos_framework::coin::{Self, Coin};
    use aptos_framework::aptos_coin::AptosCoin;

    struct Vault has key {
        funds: Coin<AptosCoin>,
        owner: address,
    }

    public entry fun open(account: &signer, deposit: Coin<AptosCoin>) {
        move_to(account, Vault { funds: deposit, owner: signer::address_of(account) });
    }

    // VULNERABLE: the auth check compares the Vault's stored owner against a
    // CALLER-SUPPLIED `claimed_owner` argument, not against the transaction
    // signer. Any attacker can pass the real owner's address as `claimed_owner`,
    // satisfy the assert, and have the extracted coins deposited to themselves.
    // The signer is only used as the payout destination — never authorized.
    public entry fun withdraw(
        caller: &signer,
        vault_addr: address,
        claimed_owner: address,
        amount: u64,
    ) acquires Vault {
        let vault = borrow_global_mut<Vault>(vault_addr);
        assert!(vault.owner == claimed_owner, 1);
        let coins = coin::extract(&mut vault.funds, amount);
        coin::deposit(signer::address_of(caller), coins);
    }

    // SAFE: read-only view of the vault balance. No state mutation, no auth
    // needed. This is the false-positive trap — must NOT be flagged.
    #[view]
    public fun balance(vault_addr: address): u64 acquires Vault {
        let vault = borrow_global<Vault>(vault_addr);
        coin::value(&vault.funds)
    }
}
