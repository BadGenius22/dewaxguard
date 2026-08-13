use anchor_lang::prelude::*;

declare_id!("BenchMissingSigner111111111111111111111111");

#[program]
pub mod missing_signer {
    use super::*;

    // VULNERABLE: authority is not checked as signer
    pub fn withdraw(ctx: Context<Withdraw>, amount: u64) -> Result<()> {
        let vault = &mut ctx.accounts.vault;
        require!(vault.balance >= amount, ErrorCode::InsufficientFunds);

        vault.balance -= amount;

        // Transfer SOL from vault to recipient
        **vault.to_account_info().try_borrow_mut_lamports()? -= amount;
        **ctx.accounts.recipient.try_borrow_mut_lamports()? += amount;

        Ok(())
    }

    // SAFE: properly checks signer (false positive trap)
    pub fn safe_withdraw(ctx: Context<SafeWithdraw>, amount: u64) -> Result<()> {
        let vault = &mut ctx.accounts.vault;
        require!(vault.balance >= amount, ErrorCode::InsufficientFunds);

        vault.balance -= amount;

        **vault.to_account_info().try_borrow_mut_lamports()? -= amount;
        **ctx.accounts.recipient.try_borrow_mut_lamports()? += amount;

        Ok(())
    }
}

#[derive(Accounts)]
pub struct Withdraw<'info> {
    #[account(mut)]
    pub vault: Account<'info, VaultState>,
    /// CHECK: no signer constraint — anyone can call
    pub authority: AccountInfo<'info>,
    /// CHECK: recipient
    #[account(mut)]
    pub recipient: AccountInfo<'info>,
}

#[derive(Accounts)]
pub struct SafeWithdraw<'info> {
    #[account(mut)]
    pub vault: Account<'info, VaultState>,
    #[account(constraint = authority.key() == vault.authority)]
    pub authority: Signer<'info>,  // Properly constrained as Signer
    /// CHECK: recipient
    #[account(mut)]
    pub recipient: AccountInfo<'info>,
}

#[account]
pub struct VaultState {
    pub authority: Pubkey,
    pub balance: u64,
}

#[error_code]
pub enum ErrorCode {
    #[msg("Insufficient funds")]
    InsufficientFunds,
}
