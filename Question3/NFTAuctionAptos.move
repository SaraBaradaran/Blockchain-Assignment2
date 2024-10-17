module 0x1::NftAuction {
    use aptos_framework::coin::{Self, Coin};
    use aptos_framework::aptos_coin::AptosCoin;
    use aptos_framework::event::EventHandle;
    use aptos_framework::event;
    use aptos_framework::vector;
    use aptos_framework::table;
    use aptos_framework::signer;
    use aptos_framework::account;

    struct Auction has key {
        seller: address,
        winner: address,
        highest_bid: u64,
        highest_bidder: address,
        token_id: u64,
        ended: bool,
        bids: table::Table<address, u64>,
        bidders: vector<address>,
        balance: Coin<AptosCoin>,
        event_bid: EventHandle<BidEvent>,
        event_auction_end: EventHandle<AuctionEndEvent>,
        event_refund: EventHandle<RefundEvent>,
        event_money_sent: EventHandle<MoneySentEvent>,
    }

    struct BidEvent has drop, store {
        bidder: address,
        price: u64,
        token_id: u64,
    }

    struct AuctionEndEvent has drop, store {
        winner: address,
        price: u64,
        token_id: u64,
    }

    struct RefundEvent has drop, store {
        nonwinner: address,
        price: u64,
        token_id: u64,
    }

    struct MoneySentEvent has drop, store {
        seller: address,
        price: u64,
        token_id: u64,
    }

    public fun initialize_auction(account: &signer, token_id: u64) {
        let seller = signer::address_of(account);
        let auction = Auction {
            seller,
            winner: seller,
            highest_bid: 0,
	          highest_bidder: seller,
            token_id,
            ended: false,
            bids: table::new<address, u64>(),
            bidders: vector::empty<address>(),
	          balance: coin::zero<AptosCoin>(),
            event_bid: account::new_event_handle<BidEvent>(account),
            event_auction_end: account::new_event_handle<AuctionEndEvent>(account),
            event_refund: account::new_event_handle<RefundEvent>(account),
            event_money_sent: account::new_event_handle<MoneySentEvent>(account)
        };
        move_to(account, auction);
    }

    // This function posts a bid and replaces the highest bid if the new bid is higher
    public fun bid(account: &signer, auction: &mut Auction, bid_amount: u64) {
        assert!(!auction.ended, 0);
        let bidder = signer::address_of(account);

        assert!(table::contains<address, u64>(&auction.bids, bidder) == false, 1);
            
        table::add(&mut auction.bids, bidder, bid_amount);
        vector::push_back(&mut auction.bidders, bidder);
            
        let coins = coin::withdraw<AptosCoin>(account, bid_amount); 
        let auction_balance_ref: &mut Coin<AptosCoin> = &mut auction.balance;
        coin::merge(auction_balance_ref, coins);
        if (bid_amount > auction.highest_bid) {
            auction.highest_bid = bid_amount;
            auction.highest_bidder = bidder;
        };

	      event::emit_event(&mut auction.event_bid, BidEvent {
            bidder: bidder, price: bid_amount, token_id: auction.token_id 
        });
	
        //If bidders reach 3, finalize the auction and transfer ownership
        if (vector::length(&auction.bidders) == 3) {
            end_auction(auction);
	          transfer_ownership(auction);
	          refund_non_winners(auction);
        }
    }

    // This function ends the auction
    fun end_auction(auction: &mut Auction) {
        assert!(!auction.ended, 2);
        auction.ended = true;
	      event::emit_event(&mut auction.event_auction_end, AuctionEndEvent { 
		        winner: auction.highest_bidder, price: auction.highest_bid, token_id: auction.token_id 
        });
    }

    // This function transfers the money to the seller
    fun transfer_ownership(auction: &mut Auction) {
	      let auction_balance_ref: &mut Coin<AptosCoin> = &mut auction.balance;
        let extracted_coins: Coin<AptosCoin> = coin::extract(auction_balance_ref, auction.highest_bid);
        coin::deposit(auction.seller, extracted_coins);
        event::emit_event(&mut auction.event_money_sent, MoneySentEvent {
            seller: auction.seller, price: auction.highest_bid, token_id: auction.token_id
        });
    }
     
    // This function refunds bids to non-winners
    fun refund_non_winners(auction: &mut Auction) {
	      let bidders_count = vector::length(&auction.bidders);
        let counter = 0;
        while (counter < bidders_count) {
            let bidder_address = *vector::borrow(&auction.bidders, counter);
	          if (auction.highest_bidder != bidder_address) {
                let money = *table::borrow(&auction.bids, bidder_address);
                let auction_balance_ref: &mut Coin<AptosCoin> = &mut auction.balance;
                let extracted_coins: Coin<AptosCoin> = coin::extract(auction_balance_ref, money);
                coin::deposit(bidder_address, extracted_coins);
                event::emit_event(&mut auction.event_refund, RefundEvent { 
                    nonwinner: bidder_address, price: money, token_id: auction.token_id 
                });		
	          }; 
            counter = counter + 1;
        }
    }
}
