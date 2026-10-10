package com.demo;

import com.demo.BankAccount;
import org.junit.Test;
import org.junit.Assert;

public class BankAccount_withdraw_Dbl_Test_Boundary_7 {

    @Test
    public void testWithdrawWithZeroAmount() {
        BankAccount account = new BankAccount("John", 100.0);
        try {
            account.withdraw(0.0);
            Assert.fail("Expected IllegalArgumentException was not thrown");
        } catch (IllegalArgumentException e) {
            Assert.assertEquals("Withdrawal must be positive", e.getMessage());
        }
    }

}
