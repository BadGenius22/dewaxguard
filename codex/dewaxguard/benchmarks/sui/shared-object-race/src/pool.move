module benchmark::pool {
    use sui::object::{Self, UID};
    use sui::transfer;
    use sui::tx_context::{Self, TxContext};
    use sui::balance::{Self, Balance};
    use sui::coin::{Self, Coin};
    use sui::sui::SUI;

    struct Pool has key {
        id: UID,
        balance: Balance<SUI>,
        total_depositors: u64,
        reward_per_depositor: u64, // Cached value, updated on deposit
    }

    // VULNERABLE: read-then-write on shared object without atomic guarantee
    // Two concurrent txs can both read old total_depositors, both increment by 1,
    // resulting in total_depositors incremented by 1 instead of 2
    public entry fun deposit(pool: &mut Pool, payment: Coin<SUI>, ctx: &mut TxContext) {
        let amount = coin::value(&payment);
        let coin_balance = coin::into_balance(payment);
        balance::join(&mut pool.balance, coin_balance);

        // Race condition: reward_per_depositor calculated from stale total
        pool.total_depositors = pool.total_depositors + 1;
        let total_balance = balance::value(&pool.balance);
        pool.reward_per_depositor = total_balance / pool.total_depositors;
    }

    // SAFE: read-only access, no race condition (false positive trap)
    public fun get_reward_estimate(pool: &Pool): u64 {
        pool.reward_per_depositor
    }

    fun init(ctx: &mut TxContext) {
        let pool = Pool {
            id: object::new(ctx),
            balance: balance::zero(),
            total_depositors: 0,
            reward_per_depositor: 0,
        };
        transfer::share_object(pool);
    }
}
