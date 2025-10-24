// contracts/pump-core/programs/pump-core/src/instructions/mod.rs

pub mod initialize;
pub mod create_token;
pub mod trade;
pub mod list_dex;
pub mod graduate_to_dex;
pub mod lp_token_lock;
pub mod security;
pub mod admin;

// Экспортируем все функции инструкций
pub use initialize::*;
pub use create_token::*;
pub use trade::*;
pub use list_dex::*;
pub use graduate_to_dex::*;
pub use lp_token_lock::*;
pub use security::*;
pub use admin::*;