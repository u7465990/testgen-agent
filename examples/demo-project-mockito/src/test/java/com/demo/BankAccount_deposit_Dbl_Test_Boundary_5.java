package com.demo;

import com.demo.BankAccount;
import org.junit.Assert;
import org.junit.Before;
import org.junit.Test;

public class BankAccount_deposit_Dbl_Test_Boundary_5 {


    private BankAccount account;

    @Before
    public void setUp() {
        account = new BankAccount("Alice", 100.0);
    }

    @Test
    public void testDepositWithZeroAmountThrowsIllegalArgumentException() {
        double amount = 0.0;
        try {
            account.deposit(amount);
            Assert.fail("Expected IllegalArgumentException for deposit amount 0.0");
        } catch (IllegalArgumentException e) {
            Assert.assertEquals("Deposit must be positive", e.getMessage());
        }
    }

}
