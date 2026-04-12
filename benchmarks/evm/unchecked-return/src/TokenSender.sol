// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract TokenSender {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    // VULNERABLE: return value of low-level call not checked properly
    function sendEth(address to, uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient");
        balances[msg.sender] -= amount;

        // Silent failure — funds deducted but never sent
        to.call{value: amount}("");
    }

    // SAFE: proper check (false positive trap)
    function safeSendEth(address to, uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient");
        balances[msg.sender] -= amount;

        (bool success, ) = to.call{value: amount}("");
        require(success, "Transfer failed");
    }

    receive() external payable {}
}
