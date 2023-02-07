from locale import currency
import sys , os


sys.path.append( os.path.abspath(os.path.curdir))
import unittest
import numpy as np

import mc.executor as simulator
from mc.executor import initialize_portfolios
from mc.utils import StrategyParams
from mc.assets import *
class TestReturnsCalculator(unittest.TestCase):
    def test_calculate_returns(self):
        # Create a test case with arbitrary values for allocated_capital
        allocated_capital = np.array([[[1, 2], [3, 4], [5, 6]]
                                    , [[7, 8], [9, 10], [11, 12]]])
        
        # Create an instance of the ReturnsCalculator class
        calculator = simulator.ReturnsCalculator(allocated_capital)
        
        # Run the calculate_returns method
        calculator.calculate_returns()
        
        # Assert that sim_portfolio is calculated correctly
        self.assertTrue(np.allclose(calculator.sim_portfolio, np.array([[3, 7, 11], [15, 19, 23]])))
        
        # Assert that sim_retuns is calculated correctly
        self.assertTrue(np.allclose(calculator.sim_retuns, np.array([[0.,1.33333333, 0.57142857], [0.,0.26666667, 0.21052632]])))
        
        # Assert that sim_cum_retuns is calculated correctly
        self.assertTrue(np.allclose(calculator.sim_cum_retuns, np.array([[1., 2.33333333, 3.66666667],[1., 1.26666667, 1.53333333] ])))



class TestPortfolioClass(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.initial_price = 100.0
        self.def_params = StrategyParams()
        self.split_params = StrategyParams(percent_allocated=0.5)
    def test_portfolio_init(self):
        sim_portfolio = initialize_portfolios(n=1,initial_price=self.initial_price,strategy_params=self.def_params)[0]
        self.assertTrue(np.allclose(sim_portfolio.capital,self.initial_price))

    def test_buy_equity_not_enough(self):
        
        portfolio = initialize_portfolios(n=1,initial_price=self.initial_price,strategy_params=self.def_params)[0]
        initial_price = portfolio.equity.initial_price
        buy_price = initial_price + 1
        buy_amount = 10
        portfolio.log_asset_price(buy_price)
        
        with self.assertRaises(NotEnoughMoney):
            portfolio.buy_equity(buy_amount)
        
    def test_buy_equity_enough(self):
        

        portfolio = initialize_portfolios(n=1,initial_price=self.initial_price,strategy_params=self.split_params)[0]
        buy_price = self.initial_price + 1
        portfolio.log_asset_price(buy_price)
        buy_amount = 0.25
        cost = buy_amount * buy_price
        initial_amount = portfolio.equity.amount
        initial_cash_amount = portfolio.cash.amount
        portfolio.buy_equity(buy_amount)

        self.assertEqual(portfolio.equity.amount, initial_amount + buy_amount)
        self.assertAlmostEqual(portfolio.equity.initial_price, (initial_amount * self.initial_price + buy_amount * buy_price) / (initial_amount + buy_amount))
        self.assertAlmostEqual(portfolio.cash.amount, initial_cash_amount-cost)
        
    def test_sell_equity(self):
        portfolio = initialize_portfolios(n=1,initial_price=self.initial_price,strategy_params=self.split_params)[0]

        initial_equity_amount = portfolio.equity.amount
        initial_cash_amount = portfolio.cash.amount
        sell_price = portfolio._equity.initial_price + 1

        portfolio.log_asset_price(sell_price)
        sell_amount = 0.25
        
        portfolio.sell_equity(sell_amount)
        
        self.assertEqual(portfolio.equity.amount, initial_equity_amount - sell_amount)
        self.assertAlmostEqual(portfolio.cash.amount, initial_cash_amount + sell_amount * sell_price)
        

    def test_rebalancer(self):
        portfolio = initialize_portfolios(n=1,initial_price=self.initial_price,strategy_params=self.split_params)[0]
        target_share = 0.5
        price_changed = 30
        portfolio.log_asset_price(price_changed)
        current_shares = portfolio.portfolio_balance
        self.assertTrue(current_shares.cash > current_shares.equity)
        portfolio.rebalance(target_share=target_share)

        new_share = portfolio.portfolio_balance
        self.assertTrue( np.isclose(new_share.cash, new_share.equity))
class TestExecutorClass(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.initial_price = 1.0
        self.split_params = StrategyParams(percent_allocated=0.5,max_rebalances=100)
        

        self.time_series = np.array([[1.,1.25,1.05,1.15,1.30,1.35]])
        self.expected_portfolio_5050_no_rebalance = np.array([[1.0, 1.125, 1.025, 1.075, 1.15, 1.175]])

        self.time_series_sudden_drop = np.array([[1.,1.10,0.49]])
        self.expected_portfolio_5050_sudden_drop_rebalance_50pct = np.array([[1.
                                                                            ,1.05 # 0.5 + 0.55 = 1.05 #first increment
                                                                            ,0.745     #0.5 + 0.5 * 0.445454 = 0.725 #portfolio  value
                                                                                        #change 0.755/2 = 0.3525
                                                                                        
                                                                            ,
                                                                            ]])

    def test_price_tracker_5050_no_rebalance(self):
        portfolios = initialize_portfolios(n=1,initial_price=self.initial_price,strategy_params=self.split_params)
        sim_tracker = simulator.SimulationTracker(self.time_series,portfolios,self.split_params)
        sim_tracker.run_simulations()

        # Create an instance of the ReturnsCalculator class
        calculator = simulator.ReturnsCalculator(sim_tracker.allocated_capital)
        
        # Run the calculate_returns method
        calculator.calculate_returns()

        
        self.assertTrue(np.allclose(calculator.sim_portfolio, self.expected_portfolio_5050_no_rebalance))
        
    def test_price_tracker_5050_rebalance_down(self):
        portfolios = initialize_portfolios(n=1,initial_price=self.initial_price,strategy_params=self.split_params)
        sim_tracker = (simulator
                        .SimulationTracker(self.time_series_sudden_drop,portfolios,self.split_params)
                        .add_rebalance_below(0.5)
                        .run_simulations()
                        )

        calculator = (simulator.ReturnsCalculator(sim_tracker.allocated_capital)
                        .calculate_returns()
                        )
        self.assertTrue(np.allclose(calculator.sim_portfolio, self.expected_portfolio_5050_sudden_drop_rebalance_50pct))

class TestDecigionLogic(unittest.TestCase):
    def test_threshold_below(self):
        
        self.assertFalse(simulator.check_is_below_threshold(current_price=1,prev_price=0.5,threshold=0.5))
        self.assertTrue(simulator.check_is_below_threshold(current_price=0.49,prev_price=1,threshold=0.5))

    def test_threshold_above(self):
        
        self.assertFalse(simulator.check_is_above_threshold(current_price=0.49,prev_price=1,threshold=0.5))
        self.assertTrue(simulator.check_is_above_threshold(current_price=1,prev_price=0.5,threshold=0.5))

if __name__ == '__main__':
    unittest.main()