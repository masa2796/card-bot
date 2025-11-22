import React, { useState } from 'react';
import { CardSummary } from '@/lib/api';
import { CardItem } from './CardItem';

type CardListProps = {
  cards: CardSummary[];
};

export const CardList: React.FC<CardListProps> = ({ cards }) => {
  const [selectedCard, setSelectedCard] = useState<CardSummary | null>(null);
  const [isEvolved, setIsEvolved] = useState(false);

  if (!cards || cards.length === 0) {
    return null;
  }

  const handleCardClick = (card: CardSummary) => {
    setSelectedCard(card);
    setIsEvolved(false);
  };

  const closeModal = () => {
    setSelectedCard(null);
  };

  return (
    <div className="mt-4">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {cards.map((card) => (
          <CardItem key={card.card_id} card={card} onClick={handleCardClick} />
        ))}
      </div>

      {/* Modal */}
      {selectedCard && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center p-4 z-50"
          onClick={closeModal}
        >
          <div 
            className="bg-gray-800 rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto transform transition-all duration-300"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="p-4 sm:p-6 border-b border-gray-700 flex justify-between items-center sticky top-0 bg-gray-800 z-10">
              <h2 className="text-2xl font-bold text-yellow-400">{selectedCard.name}</h2>
              <button onClick={closeModal} className="text-gray-400 hover:text-white transition duration-200 focus:outline-none">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
              </button>
            </div>

            {/* Content */}
            <div className="p-4 sm:p-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Left: Image & Basic Info */}
              <div className="flex flex-col items-center">
                <div className="flex space-x-2 mb-4 bg-gray-700 p-1 rounded-lg">
                  <button 
                    onClick={() => setIsEvolved(false)}
                    className={`font-semibold py-2 px-4 rounded-lg text-sm transition-colors ${!isEvolved ? 'bg-yellow-600 text-white' : 'text-gray-300 hover:bg-gray-600'}`}
                  >
                    進化前
                  </button>
                  <button 
                    onClick={() => setIsEvolved(true)}
                    className={`font-semibold py-2 px-4 rounded-lg text-sm transition-colors ${isEvolved ? 'bg-yellow-600 text-white' : 'text-gray-300 hover:bg-gray-600'}`}
                  >
                    進化後
                  </button>
                </div>

                <img 
                  src={isEvolved ? selectedCard.image_after : selectedCard.image_before} 
                  alt={selectedCard.name} 
                  className="w-2/3 max-w-xs rounded-xl shadow-lg border-2 border-yellow-500 transition-all duration-300"
                />
                
                <div className="mt-4 text-center space-y-1 text-lg">
                  <p className="text-2xl font-mono text-yellow-300">
                    {selectedCard.cost} PP / {selectedCard.attack}/{selectedCard.hp}
                  </p>
                  <p className="text-gray-300 text-sm">
                    <span className="font-semibold">クラス:</span> {selectedCard.class}
                  </p>
                  <p className="text-gray-300 text-sm">
                    <span className="font-semibold">レアリティ:</span> {selectedCard.rarity}
                  </p>
                </div>
              </div>

              {/* Right: Effect Text */}
              <div className="bg-gray-700 p-4 rounded-xl shadow-inner flex flex-col overflow-y-auto max-h-[400px]">
                <div>
                  <h3 className="text-xl font-bold mb-2 text-yellow-400 border-b border-yellow-400 pb-1">
                    {isEvolved ? '進化後効果' : '進化前効果'}
                  </h3>
                  <p className="text-gray-200 whitespace-pre-wrap">
                    {selectedCard.effect}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {selectedCard.keywords.map((keyword, idx) => (
                      <span key={idx} className="px-3 py-1 bg-yellow-500 text-gray-900 text-xs font-bold rounded-full shadow-md">
                        {keyword}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
