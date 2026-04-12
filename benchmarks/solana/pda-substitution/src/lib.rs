use anchor_lang::prelude::*;

declare_id!("BenchPDASubstitution1111111111111111111111");

#[program]
pub mod pda_substitution {
    use super::*;

    pub fn initialize(ctx: Context<Initialize>, bump: u8) -> Result<()> {
        let config = &mut ctx.accounts.config;
        config.admin = ctx.accounts.admin.key();
        config.treasury = ctx.accounts.treasury.key();
        config.bump = bump;
        Ok(())
    }

    // VULNERABLE: config PDA not verified against expected seeds
    pub fn claim_reward(ctx: Context<ClaimReward>, amount: u64) -> Result<()> {
        let config = &ctx.accounts.config;

        // Attacker can pass a fake config account with their own treasury
        **ctx.accounts.treasury.try_borrow_mut_lamports()? += amount;
        **ctx.accounts.reward_pool.try_borrow_mut_lamports()? -= amount;

        Ok(())
    }
}

#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(
        init,
        payer = admin,
        space = 8 + 32 + 32 + 1,
        seeds = [b"config", admin.key().as_ref()],
        bump
    )]
    pub config: Account<'info, Config>,
    #[account(mut)]
    pub admin: Signer<'info>,
    /// CHECK: treasury address
    pub treasury: AccountInfo<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct ClaimReward<'info> {
    // VULNERABLE: no seeds constraint — any Account<Config> accepted
    pub config: Account<'info, Config>,
    /// CHECK: treasury from config
    #[account(mut)]
    pub treasury: AccountInfo<'info>,
    /// CHECK: reward pool
    #[account(mut)]
    pub reward_pool: AccountInfo<'info>,
}

#[account]
pub struct Config {
    pub admin: Pubkey,
    pub treasury: Pubkey,
    pub bump: u8,
}
