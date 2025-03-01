import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';

// Types
interface Product {
  id: number;
  name: string;
  description: string;
  price: number;
  image_url: string | null;
  available_qty: number;
  min_group_size: number;
  discount_percentage: number;
  discount_tiers: DiscountTier[] | null;
}

interface DiscountTier {
  id: number;
  group_size: number;
  discount_percentage: number;
}

interface GroupBuy {
  id: number;
  product_id: number;
  current_count: number;
  target_count: number;
  is_active: boolean;
}

const GroupBuyingPage: React.FC = () => {
  const { productId } = useParams<{ productId: string }>();
  const navigate = useNavigate();
  const [product, setProduct] = useState<Product | null>(null);
  const [groupBuy, setGroupBuy] = useState<GroupBuy | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [joining, setJoining] = useState<boolean>(false);

  // Load product and group buy data
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        // Fetch product details
        const productResponse = await axios.get(`/api/products/${productId}`);
        setProduct(productResponse.data);
        
        // Fetch active group buy for this product
        const groupBuyResponse = await axios.get(`/api/groups/active/product/${productId}`);
        setGroupBuy(groupBuyResponse.data);
        
        setLoading(false);
      } catch (err) {
        setError('Failed to load product data. Please try again later.');
        setLoading(false);
        console.error('Error fetching product data:', err);
      }
    };
    
    fetchData();
  }, [productId]);

  // Calculate the current tier discount
  const calculateDiscount = () => {
    if (!product || !groupBuy) return 0;
    
    // If there are tiered discounts, find the applicable one
    if (product.discount_tiers && product.discount_tiers.length > 0) {
      // Sort tiers by group size (descending)
      const sortedTiers = [...product.discount_tiers].sort((a, b) => b.group_size - a.group_size);
      
      // Find the highest tier that applies to the current group size
      for (const tier of sortedTiers) {
        if (groupBuy.current_count >= tier.group_size) {
          return tier.discount_percentage;
        }
      }
    }
    
    // If no tiers or no applicable tier, use the default discount
    return groupBuy.current_count >= product.min_group_size 
      ? product.discount_percentage 
      : 0;
  };

  // Calculate discounted price
  const calculateDiscountedPrice = () => {
    if (!product) return 0;
    const discount = calculateDiscount();
    return product.price * (1 - (discount / 100));
  };
  
  // Join the group buy
  const handleJoinGroup = async () => {
    if (!product || !groupBuy) return;
    
    try {
      setJoining(true);
      
      // Create an order with 10% deposit
      const depositAmount = product.price * 0.1;
      
      const response = await axios.post('/api/orders/join-group', {
        product_id: product.id,
        group_buy_id: groupBuy.id,
        quantity: 1,
        deposit_amount: depositAmount
      });
      
      // Redirect to payment page
      navigate(`/payment/${response.data.order_id}`);
      
    } catch (err) {
      setError('Failed to join group. Please try again later.');
      setJoining(false);
      console.error('Error joining group:', err);
    }
  };

  if (loading) {
    return <div className="p-4 text-center">Loading product data...</div>;
  }

  if (error) {
    return <div className="p-4 text-center text-red-500">{error}</div>;
  }

  if (!product) {
    return <div className="p-4 text-center">Product not found</div>;
  }

  return (
    <div className="max-w-md mx-auto bg-white rounded-lg shadow-md overflow-hidden md:max-w-2xl m-4">
      <div className="md:flex">
        <div className="md:flex-shrink-0">
          {product.image_url ? (
            <img 
              className="h-48 w-full object-cover md:w-48" 
              src={product.image_url} 
              alt={product.name} 
            />
          ) : (
            <div className="h-48 w-full bg-gray-200 flex items-center justify-center md:w-48">
              <span className="text-gray-500">No image</span>
            </div>
          )}
        </div>
        
        <div className="p-8">
          <div className="uppercase tracking-wide text-sm text-indigo-500 font-semibold">
            Group Buying
          </div>
          
          <h1 className="mt-1 text-lg font-medium text-gray-900">
            {product.name}
          </h1>
          
          <p className="mt-2 text-gray-600">
            {product.description}
          </p>
          
          <div className="mt-4">
            <div className="flex items-center justify-between">
              <span className="text-gray-600">Regular Price:</span>
              <span className="font-bold">${product.price.toFixed(2)}</span>
            </div>
            
            {calculateDiscount() > 0 && (
              <div className="flex items-center justify-between mt-1">
                <span className="text-green-600">Discounted Price:</span>
                <span className="font-bold text-green-600">
                  ${calculateDiscountedPrice().toFixed(2)}
                </span>
              </div>
            )}
          </div>
          
          {groupBuy && (
            <div className="mt-4 bg-gray-100 p-4 rounded-lg">
              <h3 className="font-medium">Group Progress</h3>
              
              <div className="mt-2 h-4 relative max-w-xl rounded-full overflow-hidden">
                <div className="w-full h-full bg-gray-200 absolute"></div>
                <div 
                  className="h-full bg-green-500 absolute" 
                  style={{ 
                    width: `${(groupBuy.current_count / groupBuy.target_count) * 100}%` 
                  }}
                ></div>
              </div>
              
              <div className="flex justify-between mt-1 text-sm">
                <span>
                  {groupBuy.current_count} of {groupBuy.target_count} buyers
                </span>
                <span>
                  {Math.round((groupBuy.current_count / groupBuy.target_count) * 100)}%
                </span>
              </div>
              
              {groupBuy.current_count < product.min_group_size && (
                <p className="text-sm text-gray-600 mt-2">
                  Need {product.min_group_size - groupBuy.current_count} more 
                  buyer(s) to unlock the {product.discount_percentage}% discount!
                </p>
              )}
            </div>
          )}
          
          {product.discount_tiers && product.discount_tiers.length > 0 && (
            <div className="mt-4">
              <h3 className="font-medium">Discount Tiers</h3>
              <ul className="mt-2 space-y-1">
                {product.discount_tiers
                  .sort((a, b) => a.group_size - b.group_size)
                  .map((tier) => (
                    <li 
                      key={tier.id}
                      className={`text-sm ${
                        groupBuy && groupBuy.current_count >= tier.group_size
                          ? 'text-green-600 font-medium'
                          : 'text-gray-600'
                      }`}
                    >
                      {tier.group_size} buyers: {tier.discount_percentage}% discount
                      {groupBuy && groupBuy.current_count >= tier.group_size && ' (Unlocked!)'}
                    </li>
                  ))}
              </ul>
            </div>
          )}
          
          <div className="mt-6">
            <button
              onClick={handleJoinGroup}
              disabled={joining || !groupBuy || !groupBuy.is_active}
              className={`px-4 py-2 rounded-md text-white font-medium w-full
                ${
                  joining || !groupBuy || !groupBuy.is_active
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-indigo-600 hover:bg-indigo-700'
                }`}
            >
              {joining 
                ? 'Processing...' 
                : !groupBuy || !groupBuy.is_active
                  ? 'Group not available'
                  : 'Join Group (10% Deposit)'}
            </button>
            
            {groupBuy && !groupBuy.is_active && (
              <p className="text-sm text-gray-600 mt-2 text-center">
                This group is no longer accepting new buyers.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default GroupBuyingPage;