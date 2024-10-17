module 0x1::NftAuction {
    use sui::coin::{Self, Coin, join};
    use sui::sui::SUI;
    use sui::event;

    public struct Auction has key {
	    id: UID,
        seller: address,
        winner: address,
        highest_bid: u64,
        highest_bidder: address,
        token_id: u64,
        ended: bool,
        bids: vector<u64>,
        bidders: vector<address>,
        balance: Coin<SUI>,
    }

    public struct BidEvent has drop, copy, store {
        bidder: address,
        price: u64,
        token_id: u64,
    }

    public struct AuctionEndEvent has drop, copy, store {
        winner: address,
        price: u64,
        token_id: u64,
    }

    public struct RefundEvent has drop, copy, store {
        nonwinner: address,
        price: u64,
        token_id: u64,
    }

    public struct MoneySentEvent has drop, copy, store {
        seller: address,
        price: u64,
        token_id: u64,
    }

    public fun initialize_auction(account: &mut TxContext, token_id: u64) {
        let seller = tx_context::sender(account);
        let auction = Auction {
            id: object::new(account),
            seller,
            winner: seller,
            highest_bid: 0,
            highest_bidder: seller,
            token_id,
            ended: false,
            bids: vector::empty<u64>(),
            bidders: vector::empty<address>(),
            balance: coin::zero<SUI>(account),
        };
  	    transfer::share_object(auction);
    }

    // This function posts a bid and replaces the highest bid if the new bid is higher
    public fun bid(tx_context: &mut TxContext, auction: &mut Auction, bid_amount: u64, sent_coin: &mut Coin<SUI>) {
        assert!(!auction.ended, 0);
        let bidder = tx_context::sender(tx_context);

        assert!(vector::contains(&auction.bidders, &bidder) == false, 1);
        let bid_coin = coin::split(sent_coin, bid_amount, tx_context);

        vector::push_back(&mut auction.bidders, bidder);
        vector::push_back(&mut auction.bids, bid_amount);    
        
        let auction_balance_ref: &mut Coin<SUI> = &mut auction.balance;
        join(auction_balance_ref, bid_coin);
        if (bid_amount > auction.highest_bid) {
            auction.highest_bid = bid_amount;
            auction.highest_bidder = bidder;
        };

        event::emit(BidEvent {
            bidder: bidder, price: bid_amount, token_id: auction.token_id 
        });
	
        //If bidders reach 3, finalize the auction and transfer ownership
        if (vector::length(&auction.bidders) == 3) {
            end_auction(auction);
            transfer_ownership(auction, tx_context);
            refund_non_winners(auction, tx_context);
        }
    }

    // This function ends the auction
    fun end_auction(auction: &mut Auction) {
        assert!(!auction.ended, 2);
        auction.ended = true;
        event::emit(AuctionEndEvent { 
            winner: auction.highest_bidder, price: auction.highest_bid, token_id: auction.token_id 
        });
    }

    // This function transfers the money to the seller
    fun transfer_ownership(auction: &mut Auction, tx_context: &mut TxContext) {
        let auction_balance_ref: &mut Coin<SUI> = &mut auction.balance;
        let extracted_coins: Coin<SUI> = coin::split(auction_balance_ref, auction.highest_bid, tx_context);
        transfer::public_transfer(extracted_coins, auction.seller);
        event::emit(MoneySentEvent {
            seller: auction.seller, price: auction.highest_bid, token_id: auction.token_id
        });
    }
     
    // This function refunds bids to non-winners
    fun refund_non_winners(auction: &mut Auction, tx_context: &mut TxContext) {
        let bidders_count = vector::length(&auction.bidders);
        let mut counter = 0;
        while (counter < bidders_count) {
        let bidder_address = *vector::borrow(&auction.bidders, counter);
            if (auction.highest_bidder != bidder_address) {
                let money = *vector::borrow(&auction.bids, counter);
                let auction_balance_ref: &mut Coin<SUI> = &mut auction.balance;
                let extracted_coins: Coin<SUI> = coin::split(auction_balance_ref, money, tx_context);
                transfer::public_transfer(extracted_coins, bidder_address);
                event::emit(RefundEvent { 
                    nonwinner: bidder_address, price: money, token_id: auction.token_id 
                });		
            }; 
            counter = counter + 1;
        }
    }
}
