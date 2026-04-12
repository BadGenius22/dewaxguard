// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC20} from "./IERC20.sol";

contract SimpleVault {
    IERC20 public immutable asset;
    mapping(address => uint256) public shares;
    uint256 public totalShares;

    constructor(address _asset) {
        asset = IERC20(_asset);
    }

    // VULNERABLE: no virtual share offset, first depositor can inflate
    function deposit(uint256 assets) external returns (uint256 sharesMinted) {
        uint256 supply = totalShares;
        uint256 totalAssets = asset.balanceOf(address(this));

        if (supply == 0) {
            sharesMinted = assets;
        } else {
            sharesMinted = (assets * supply) / totalAssets; // Inflatable denominator
        }

        require(sharesMinted > 0, "Zero shares");
        shares[msg.sender] += sharesMinted;
        totalShares += sharesMinted;
        asset.transferFrom(msg.sender, address(this), assets);
    }

    function withdraw(uint256 sharesToBurn) external returns (uint256 assetsOut) {
        require(shares[msg.sender] >= sharesToBurn, "Insufficient shares");

        uint256 totalAssets = asset.balanceOf(address(this));
        assetsOut = (sharesToBurn * totalAssets) / totalShares;

        shares[msg.sender] -= sharesToBurn;
        totalShares -= sharesToBurn;
        asset.transfer(msg.sender, assetsOut);
    }
}

interface IERC20 {
    function balanceOf(address) external view returns (uint256);
    function transfer(address, uint256) external returns (bool);
    function transferFrom(address, address, uint256) external returns (bool);
}
