#![no_std]
use soroban_sdk::{contract, contractimpl, Address, Env};

#[contract]
pub struct Token;

#[contractimpl]
impl Token {
    pub fn balance(env: Env, who: Address) -> i128 {
        env.storage().persistent().get(&who).unwrap_or(0)
    }

    // VULNERABLE: transfer debits `from`'s persistent balance but never calls
    // `from.require_auth()`. On Soroban, moving another address's funds REQUIRES
    // an explicit require_auth on that address — without it any caller can move
    // anyone else's balance. Permissionless theft.
    pub fn transfer(env: Env, from: Address, to: Address, amount: i128) {
        let bal_from: i128 = env.storage().persistent().get(&from).unwrap_or(0);
        let bal_to: i128 = env.storage().persistent().get(&to).unwrap_or(0);
        env.storage().persistent().set(&from, &(bal_from - amount));
        env.storage().persistent().set(&to, &(bal_to + amount));
    }

    // SAFE: burn DOES call from.require_auth() before debiting — this is the
    // correct pattern and the false-positive trap. It must NOT be flagged as
    // missing-auth, and it is the precedent that proves transfer() is the bug.
    pub fn burn(env: Env, from: Address, amount: i128) {
        from.require_auth();
        let bal_from: i128 = env.storage().persistent().get(&from).unwrap_or(0);
        env.storage().persistent().set(&from, &(bal_from - amount));
    }
}
