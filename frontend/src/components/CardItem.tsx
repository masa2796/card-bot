import React from 'react';
import { CardSummary } from '@/lib/api';

type CardItemProps = {
  card: CardSummary;
  onClick: (card: CardSummary) => void;
};

export const CardItem: React.FC<CardItemProps> = ({ card, onClick }) => {
  let rarityColor = 'border-gray-500';
  if (card.rarity.includes('レジェンド')) rarityColor = 'border-yellow-500';
  else if (card.rarity.includes('ゴールド')) rarityColor = 'border-amber-400';
  else if (card.rarity.includes('シルバー')) rarityColor = 'border-slate-400';

  return (
    <div 
      className="relative bg-gray-800 rounded-lg overflow-hidden shadow-lg hover:shadow-xl hover:scale-[1.02] transition duration-300 cursor-pointer border border-gray-700"
      onClick={() => onClick(card)}
    >
      {/* カード画像 */}
      <img 
        src={card.image_before} 
        alt={card.name} 
        className={`w-full h-auto object-cover ${rarityColor} border-b-4`}
      />
     {/* クラス (右上) */}
      <div className="absolute top-2 right-2 px-2 py-0.5 bg-green-700 text-white text-xs font-semibold rounded-full shadow-md">
        {card.class}
      </div>

      {/* カード名と基本ステータス (下部) */}
      <div className="p-2 text-center">
        <p className="text-sm font-semibold truncate text-gray-100">{card.name}</p>
        <p className="text-xs text-gray-400">{card.attack}/{card.hp} ({card.rarity})</p>
      </div>
    </div>
  );
};
