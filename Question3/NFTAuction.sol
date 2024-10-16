// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract NFTAuction {

    address seller;
    address winner;
    uint256 highestBid;
    address highestBidder;
    uint256 tokenId;
    bool ended;

    mapping(address => uint256) public bids;
    address[] public bidders;

    event NewBid(address indexed bidder, uint256 price, uint256 tokenId);
    event AuctionEnded(address indexed winner, uint256 price, uint256 tokenId);
    event MoneySent(address indexed seller, uint256 price, uint256 tokenId);

    constructor(uint256 nftId) {
        seller = msg.sender;
        tokenId = nftId;
        ended = false;
        winner = address(0);
        highestBid = 0;
        highestBidder = address(0);
    }

    // This function posts a bid and replaces the highest bid if the new bid is higher
    function bid() payable external {
        require(!ended, "Auction ended");
        require(bids[msg.sender] == 0, "Bidder already placed bid");
        bids[msg.sender] = msg.value;
        bidders.push(msg.sender);
        if (msg.value > highestBid) {
            highestBid = msg.value;
            highestBidder = msg.sender;
        }
        emit NewBid(msg.sender, msg.value, tokenId);
        // If bidders reach 3, finalize the auction and transfer ownership
        if (bidders.length == 3) {
            endAuction();
            transferOwnership();
            refundNonWinners();
        }
    }

    // This function ends the auction
    function endAuction() internal {
        require(!ended, "Auction already ended");
        ended = true;
        emit AuctionEnded(highestBidder, highestBid, tokenId);
    }

    // This function transfers the money to the seller
    function transferOwnership() internal {
        payable(seller).transfer(highestBid);
        emit MoneySent(seller, highestBid, tokenId);
    }

    // This function refunds bids to non-winners
    function refundNonWinners() internal {
        for (uint i = 0; i < bidders.length; i++) {
            if (bidders[i] != highestBidder) {
                uint256 money = bids[bidders[i]];
                payable(bidders[i]).transfer(money);
            }
        }
    }
}
